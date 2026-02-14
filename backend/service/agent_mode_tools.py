"""
Agent Mode Tools for ComfyUI-Copilot
Autonomous multi-step workflow creation, execution, and iteration.

Enhanced by Claude Opus 4.6
"""

import json
import re
import time
import copy
from typing import Dict, Any, Optional, List

try:
    from agents.tool import function_tool
    if not hasattr(__import__('agents'), 'Agent'):
        raise ImportError
except Exception:
    raise ImportError(
        "Detected incorrect or missing 'agents' package while loading agent mode tools. "
        "Please install 'openai-agents' and ensure this plugin prefers it."
    )

from ..dao.workflow_table import get_workflow_data, save_workflow_data, get_workflow_data_by_id
from ..utils.comfy_gateway import ComfyGateway, get_object_info, get_object_info_by_class
from ..utils.request_context import get_session_id, get_config
from ..utils.logger import log


# ---------------------------------------------------------------------------
# Object-info cache — /api/object_info is huge (10-50 MB) and never changes
# during a session.  Caching it avoids repeated multi-second fetches that
# amplify tool-call timeouts on local models.
# ---------------------------------------------------------------------------

_object_info_cache: dict = {}
_object_info_cache_time: float = 0.0
_OBJECT_INFO_TTL = 300.0   # 5-minute TTL


async def _get_cached_object_info() -> dict:
    """Return cached /api/object_info, refreshing if stale."""
    global _object_info_cache, _object_info_cache_time
    now = time.time()
    if _object_info_cache and (now - _object_info_cache_time) < _OBJECT_INFO_TTL:
        return _object_info_cache
    try:
        data = await get_object_info()
        if data:
            _object_info_cache = data
            _object_info_cache_time = now
        return data or _object_info_cache  # return stale cache on failure
    except Exception:
        return _object_info_cache  # stale is better than empty


# ---------------------------------------------------------------------------
# Task Queue — lightweight in-memory task tracker scoped to a single run
# ---------------------------------------------------------------------------

class TaskQueue:
    """Simple task queue for agent planning and execution tracking."""

    def __init__(self):
        self.tasks: List[Dict[str, Any]] = []
        self._counter = 0

    def add_task(self, title: str, description: str = "") -> int:
        self._counter += 1
        task = {
            "id": self._counter,
            "title": title,
            "description": description,
            "status": "pending",       # pending | in_progress | completed | failed | skipped
            "result": None,
            "created_at": time.time(),
        }
        self.tasks.append(task)
        return self._counter

    def start_task(self, task_id: int) -> bool:
        for t in self.tasks:
            if t["id"] == task_id:
                t["status"] = "in_progress"
                return True
        return False

    def complete_task(self, task_id: int, result: str = "") -> bool:
        for t in self.tasks:
            if t["id"] == task_id:
                t["status"] = "completed"
                t["result"] = result
                return True
        return False

    def fail_task(self, task_id: int, reason: str = "") -> bool:
        for t in self.tasks:
            if t["id"] == task_id:
                t["status"] = "failed"
                t["result"] = reason
                return True
        return False

    def skip_task(self, task_id: int, reason: str = "") -> bool:
        for t in self.tasks:
            if t["id"] == task_id:
                t["status"] = "skipped"
                t["result"] = reason
                return True
        return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "total": len(self.tasks),
            "pending": sum(1 for t in self.tasks if t["status"] == "pending"),
            "in_progress": sum(1 for t in self.tasks if t["status"] == "in_progress"),
            "completed": sum(1 for t in self.tasks if t["status"] == "completed"),
            "failed": sum(1 for t in self.tasks if t["status"] == "failed"),
            "tasks": self.tasks,
        }

    def next_pending(self) -> Optional[Dict[str, Any]]:
        for t in self.tasks:
            if t["status"] == "pending":
                return t
        return None


# Module-level queue instance — reset per agent run
_task_queue = TaskQueue()


def reset_task_queue():
    """Reset the task queue for a new agent run."""
    global _task_queue
    _task_queue = TaskQueue()


def get_task_queue() -> TaskQueue:
    return _task_queue


# ---------------------------------------------------------------------------
# Tool Call Tracker — hard-limits per-tool invocations so the LLM can't loop
# ---------------------------------------------------------------------------

class ToolCallTracker:
    """
    Enforces per-tool call limits.  When a tool exceeds its budget, the tool
    returns an error string that the LLM will see, forcing it to stop.
    """

    # Per-tool limits (tool_name → max allowed calls)
    DEFAULT_LIMITS: Dict[str, int] = {
        "search_nodes":         4,
        "get_node_details":     6,
        "list_available_models": 4,
        "plan_tasks":           3,
        "validate_workflow":    5,
        "execute_workflow":     3,
        "check_execution_result": 5,
        "save_workflow":        5,
    }
    GLOBAL_LIMIT = 30  # absolute max across ALL tool calls

    def __init__(self):
        self._counts: Dict[str, int] = {}
        self._total = 0

    def check(self, tool_name: str) -> Optional[str]:
        """
        Call BEFORE executing a tool.
        Returns None if OK, or an error string if the limit is exceeded.
        """
        self._total += 1
        self._counts[tool_name] = self._counts.get(tool_name, 0) + 1

        count = self._counts[tool_name]
        limit = self.DEFAULT_LIMITS.get(tool_name)

        if self._total > self.GLOBAL_LIMIT:
            return (
                f"GLOBAL TOOL LIMIT REACHED ({self.GLOBAL_LIMIT} calls). "
                "You MUST stop calling tools and report your current results to the user NOW."
            )

        if limit and count > limit:
            return (
                f"TOOL LIMIT: '{tool_name}' has been called {count} times (max {limit}). "
                "STOP calling this tool. Use the results you already have, "
                "or tell the user what is missing and suggest alternatives."
            )

        return None  # OK to proceed

    def get_count(self, tool_name: str) -> int:
        return self._counts.get(tool_name, 0)


# Module-level tracker — reset per agent run
_tool_tracker = ToolCallTracker()


def reset_tool_tracker():
    """Reset the tool call tracker for a new agent run."""
    global _tool_tracker
    _tool_tracker = ToolCallTracker()


def get_tool_tracker() -> ToolCallTracker:
    return _tool_tracker


# ---------------------------------------------------------------------------
# Agent Mode tools (decorated with @function_tool for the openai-agents SDK)
# ---------------------------------------------------------------------------

@function_tool
def plan_tasks(tasks: list[str]) -> str:
    """Create a step-by-step plan. Call first."""
    limit_err = get_tool_tracker().check("plan_tasks")
    if limit_err:
        return json.dumps({"error": limit_err})
    queue = get_task_queue()
    created = []
    for desc in tasks:
        tid = queue.add_task(title=desc)
        created.append({"id": tid, "title": desc, "status": "pending"})
    return json.dumps({"plan": created, "total_steps": len(created)})


@function_tool
def update_task_status(task_id: int, status: str, result: str = "") -> str:
    """Set task status: in_progress|completed|failed|skipped"""
    queue = get_task_queue()
    ok = False
    if status == "in_progress":
        ok = queue.start_task(task_id)
    elif status == "completed":
        ok = queue.complete_task(task_id, result)
    elif status == "failed":
        ok = queue.fail_task(task_id, result)
    elif status == "skipped":
        ok = queue.skip_task(task_id, result)

    if not ok:
        return json.dumps({"error": f"Task {task_id} not found or invalid status '{status}'"})

    return json.dumps(queue.get_status())


@function_tool
def get_plan_status(reason: str = "check") -> str:
    """Get all tasks and their statuses."""
    return json.dumps(get_task_queue().get_status())


@function_tool
def get_current_workflow_for_agent(reason: str = "inspect") -> str:
    """Get current session workflow JSON."""
    session_id = get_session_id()
    if not session_id:
        return json.dumps({"error": "No session_id found in context"})
    workflow_data = get_workflow_data(session_id)
    if not workflow_data:
        return json.dumps({"info": "No workflow exists yet for this session. You may need to build one from scratch."})
    # Truncate huge workflows to avoid blowing the model's context window.
    # The agent only needs to know what nodes exist, not every detail.
    raw = json.dumps(workflow_data, ensure_ascii=False)
    if len(raw) > 3000:
        # Return a summary: list of node IDs, class types, and a truncation note
        summary_nodes = {}
        for nid, ndata in workflow_data.items():
            if isinstance(ndata, dict):
                summary_nodes[nid] = {
                    "class_type": ndata.get("class_type", "unknown"),
                }
        return json.dumps({
            "node_count": len(summary_nodes),
            "nodes": summary_nodes,
            "note": "Workflow truncated. Use save_workflow with full JSON to update.",
        })
    return raw


def _robust_json_loads(raw: str) -> Any:
    """Try multiple strategies to parse JSON that the LLM may have mangled."""
    # 1. Direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. Fix invalid escape sequences (\n \t are fine, but \/ \' etc. aren't)
    #    Replace lone backslashes that aren't valid JSON escapes
    try:
        fixed = re.sub(
            r'\\(?!["\\bfnrtu/])',  # backslash NOT followed by valid escape char
            r'\\\\',               # replace with double-backslash
            raw,
        )
        return json.loads(fixed)
    except (json.JSONDecodeError, re.error):
        pass

    # 3. Strip markdown code fences the LLM sometimes wraps around JSON
    stripped = re.sub(r'^```(?:json)?\s*', '', raw.strip())
    stripped = re.sub(r'\s*```$', '', stripped)
    if stripped != raw.strip():
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

    # 4. Last resort: strict=False (allows control chars)
    try:
        return json.loads(raw, strict=False)
    except json.JSONDecodeError:
        pass

    raise json.JSONDecodeError("All parse strategies failed", raw, 0)


@function_tool
def save_workflow(workflow_json: str, description: str = "Agent mode checkpoint") -> str:
    """Save workflow JSON. Pass MCP output exactly as-is."""
    limit_err = get_tool_tracker().check("save_workflow")
    if limit_err:
        return json.dumps({"error": limit_err})
    session_id = get_session_id()
    if not session_id:
        return json.dumps({"error": "No session_id found in context"})
    try:
        data = _robust_json_loads(workflow_json) if isinstance(workflow_json, str) else workflow_json
        version_id = save_workflow_data(
            session_id,
            data,
            attributes={"action": "agent_mode_save", "description": description},
        )
        # Return ext data so the frontend applies the workflow to the canvas.
        # The agent_mode.py _process_events() extracts the "ext" key from tool
        # outputs and propagates it through to the frontend MessageList, which
        # looks for type="workflow_update" and calls applyNewWorkflow().
        return json.dumps({
            "success": True,
            "version_id": version_id,
            "ext": [
                {
                    "type": "workflow_update",
                    "data": {"workflow_data": data},
                },
                {
                    "type": "workflow_update_complete",
                    "data": {
                        "checkpoint_id": version_id,
                        "description": description,
                    },
                },
            ],
        })
    except Exception as e:
        return json.dumps({"error": f"Failed to save workflow: {str(e)}"})


@function_tool
async def validate_workflow(reason: str = "check") -> str:
    """Validate current workflow for errors. Does NOT run it."""
    limit_err = get_tool_tracker().check("validate_workflow")
    if limit_err:
        return json.dumps({"error": limit_err})
    session_id = get_session_id()
    if not session_id:
        return json.dumps({"error": "No session_id found in context"})
    workflow_data = get_workflow_data(session_id)
    if not workflow_data:
        return json.dumps({"error": "No workflow data found to validate"})
    try:
        gateway = ComfyGateway()
        request_data = {
            "prompt": workflow_data,
            "client_id": f"agent_mode_{session_id}",
        }
        result = await gateway.run_prompt(request_data)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": f"Validation failed: {str(e)}"})


@function_tool
async def execute_workflow(reason: str = "run") -> str:
    """Execute current workflow. Returns prompt_id."""
    limit_err = get_tool_tracker().check("execute_workflow")
    if limit_err:
        return json.dumps({"error": limit_err})
    session_id = get_session_id()
    if not session_id:
        return json.dumps({"error": "No session_id found in context"})
    workflow_data = get_workflow_data(session_id)
    if not workflow_data:
        return json.dumps({"error": "No workflow data found to execute"})
    try:
        gateway = ComfyGateway()
        request_data = {
            "prompt": workflow_data,
            "client_id": f"agent_mode_{session_id}",
        }
        result = await gateway.run_prompt(request_data)
        if result.get("success"):
            prompt_id = result.get("prompt_id")
            return json.dumps({
                "success": True,
                "prompt_id": prompt_id,
                "message": "Workflow queued for execution. Use check_execution_result to monitor progress.",
            })
        else:
            return json.dumps({
                "success": False,
                "error": result.get("error", "Unknown error"),
                "node_errors": result.get("node_errors", {}),
            })
    except Exception as e:
        return json.dumps({"error": f"Execution failed: {str(e)}"})


@function_tool
async def check_execution_result(prompt_id: str) -> str:
    """Check if execution is done. Returns outputs."""
    try:
        gateway = ComfyGateway()
        history = await gateway.get_history(prompt_id)
        if not history:
            # Check queue status
            queue_status = await gateway.get_queue_status()
            running = queue_status.get("queue_running", [])
            pending = queue_status.get("queue_pending", [])
            is_running = any(item[1] == prompt_id for item in running)
            is_pending = any(item[1] == prompt_id for item in pending)
            if is_running:
                return json.dumps({"status": "running", "message": "Workflow is currently executing..."})
            elif is_pending:
                return json.dumps({"status": "pending", "message": "Workflow is queued, waiting to start..."})
            else:
                return json.dumps({"status": "unknown", "message": "Prompt ID not found in queue or history. It may still be processing."})
        
        # Extract outputs
        outputs = history.get("outputs", {})
        output_summary = {}
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                output_summary[node_id] = {
                    "type": "images",
                    "images": [
                        {"filename": img.get("filename"), "subfolder": img.get("subfolder", ""), "type": img.get("type", "output")}
                        for img in node_output["images"]
                    ],
                }
            elif "text" in node_output:
                output_summary[node_id] = {"type": "text", "text": node_output["text"]}
        
        return json.dumps({
            "status": "completed",
            "outputs": output_summary,
            "message": f"Execution completed. {len(output_summary)} node(s) produced output.",
        })
    except Exception as e:
        return json.dumps({"error": f"Failed to check result: {str(e)}"})


@function_tool
async def search_nodes(query: str, keywords: list[str] = None, limit: int = 5) -> str:
    """Search installed ComfyUI nodes by name/category."""
    limit_err = get_tool_tracker().check("search_nodes")
    if limit_err:
        return json.dumps({"error": limit_err})
    try:
        object_info = await _get_cached_object_info()
        if not object_info:
            return json.dumps({"error": "Failed to fetch node info from ComfyUI"})

        tokens = []
        if query:
            tokens.append(query.lower())
        if keywords:
            tokens.extend([kw.lower() for kw in keywords if kw.strip()])

        if not tokens:
            return json.dumps({"error": "No search query provided"})

        candidates = []
        for cls_name, meta in object_info.items():
            if not isinstance(meta, dict):
                continue
            # Build searchable text from node metadata
            # Use `or ""` to guard against None values in metadata
            search_text = " ".join([
                cls_name.lower(),
                (meta.get("display_name") or "").lower(),
                (meta.get("category") or "").lower(),
                (meta.get("description") or "").lower(),
            ])
            score = sum(1 for t in tokens if t in search_text)
            if score > 0:
                candidates.append((score, cls_name, meta.get("display_name") or cls_name, meta.get("category") or ""))

        candidates.sort(key=lambda x: -x[0])
        # Cap at limit (default 5) to keep token usage low
        capped = min(limit, 5)
        results = [
            {"class_name": c[1], "display_name": c[2], "category": c[3]}
            for c in candidates[:capped]
        ]
        return json.dumps({"results": results, "total_found": len(candidates)})
    except Exception as e:
        return json.dumps({"error": f"Search failed: {str(e)}"})


@function_tool
async def get_node_details(node_class: str) -> str:
    """Get input/output spec for a node class."""
    limit_err = get_tool_tracker().check("get_node_details")
    if limit_err:
        return json.dumps({"error": limit_err})
    try:
        info = await get_object_info_by_class(node_class)
        if info:
            return json.dumps(info, ensure_ascii=False)
        # Fallback: fuzzy search
        object_info = await get_object_info()
        similar = [k for k in object_info.keys() if node_class.lower() in k.lower()]
        if similar:
            return json.dumps({"error": f"Node '{node_class}' not found", "suggestions": similar[:5]})
        return json.dumps({"error": f"Node '{node_class}' not found and no similar nodes detected"})
    except Exception as e:
        return json.dumps({"error": f"Failed to get node details: {str(e)}"})


@function_tool
async def list_available_models(model_type: str = "checkpoints") -> str:
    """List model files by type: checkpoints|loras|vae|controlnet|upscale_models|embeddings|clip"""
    limit_err = get_tool_tracker().check("list_available_models")
    if limit_err:
        return json.dumps({"error": limit_err})
    try:
        import folder_paths
        type_map = {
            "checkpoints": "checkpoints",
            "loras": "loras",
            "vae": "vae",
            "controlnet": "controlnet",
            "upscale_models": "upscale_models",
            "embeddings": "embeddings",
            "clip": "clip",
        }
        folder_name = type_map.get(model_type.lower(), model_type)
        try:
            models = folder_paths.get_filename_list(folder_name)
            # Cap at 20 to keep tool output small for token-constrained models
            return json.dumps({
                "model_type": model_type,
                "count": len(models),
                "models": models[:20],
                "truncated": len(models) > 20,
            })
        except Exception:
            return json.dumps({"error": f"Unknown model type: '{model_type}'. Valid types: {list(type_map.keys())}"})
    except Exception as e:
        return json.dumps({"error": f"Failed to list models: {str(e)}"})
