'''
All-in-one Single Agent for Chat + Debug + Rewrite (streaming)
'''
from typing import List, Dict, Any, Optional
import asyncio
import traceback

from ..utils.globals import BACKEND_BASE_URL, get_comfyui_copilot_api_key, WORKFLOW_MODEL_NAME
from ..utils.logger import log
from ..utils.request_context import get_session_id, get_config
from ..utils.key_utils import workflow_config_adapt

# OpenAI Agents SDK imports
try:
    from agents._config import set_default_openai_api
    from agents.items import ItemHelpers
    from agents.mcp import MCPServerSse
    from agents.run import Runner
    from agents.tracing import set_tracing_disabled
except Exception:
    raise ImportError(
        "Detected incorrect or missing 'agents' package while loading All-in-one agent. "
        "Please install 'openai-agents'. Commands:\n"
        "  python -m pip uninstall -y agents gym tensorflow\n"
        "  python -m pip install -U openai-agents"
    )

from openai.types.responses import ResponseTextDeltaEvent

# Import tools from existing modules
from .debug_agent import run_workflow, analyze_error_type, save_current_workflow
from .link_agent_tools import analyze_missing_connections, apply_connection_fixes
from .workflow_rewrite_tools import get_current_workflow, get_node_info, update_workflow, remove_node
from .parameter_tools import (
    find_matching_parameter_value,
    get_model_files,
    suggest_model_download,
    update_workflow_parameter,
)

from ..agent_factory import create_agent


async def all_in_one_invoke(messages: List[Dict[str, Any]], images: Optional[List[Any]] = None):
    """
    Invoke a single agent that can handle chat, debug, and rewrite in one place.

    Yields tuples of (accumulated_text, {"data": ext_or_None, "finished": bool}).
    """
    try:
        session_id = get_session_id()
        config = get_config()
        if not session_id:
            raise ValueError("No session_id found in request context")
        if not config:
            raise ValueError("No config found in request context")

        # Adapt config if needed (keys, endpoints, etc.)
        config = workflow_config_adapt(config)

        # Prepare MCP servers to expose external tools (recall_workflow, gen_workflow, searches, etc.)
        mcp_server = MCPServerSse(
            params={
                "url": BACKEND_BASE_URL + "/mcp-server/mcp",
                "timeout": 300.0,
                "headers": {"X-Session-Id": session_id, "Authorization": f"Bearer {get_comfyui_copilot_api_key()}"}
            },
            cache_tools_list=True,
            client_session_timeout_seconds=300.0
        )

        bing_server = MCPServerSse(
            params={
                "url": "https://mcp.api-inference.modelscope.net/8c9fe550938e4f/sse",
                "timeout": 300.0,
                "headers": {"X-Session-Id": session_id, "Authorization": f"Bearer {get_comfyui_copilot_api_key()}"}
            },
            cache_tools_list=True,
            client_session_timeout_seconds=300.0
        )

        async with mcp_server, bing_server:
            agent = create_agent(
                name="ComfyUI-AllInOne",
                model=WORKFLOW_MODEL_NAME,
                instructions=(
                    "You are a single powerful assistant for ComfyUI.\n\n"
                    "- Respond in the user's language.\n"
                    "- For workflow generation requests, ALWAYS call recall_workflow first, then gen_workflow, and merge results.\n"
                    "- For debug intents (workflow failed, node error): validate with run_workflow(), analyze with analyze_error_type(), then use link/parameter/rewrite tools accordingly and re-validate.\n"
                    "- For rewrite intents (modify current canvas): use get_current_workflow(), get_node_info(), update_workflow(), remove_node(), and ensure connections/types are valid.\n"
                    "- Prefer concise streaming updates.\n"
                ),
                # Bind ALL local tools
                tools=[
                    # Debug/validation
                    run_workflow, analyze_error_type, save_current_workflow,
                    # Link/connectivity
                    analyze_missing_connections, apply_connection_fixes,
                    # Rewrite/structure
                    get_current_workflow, get_node_info, update_workflow, remove_node,
                    # Parameters/models
                    find_matching_parameter_value, get_model_files, suggest_model_download, update_workflow_parameter,
                ],
                # Expose MCP tool servers for chat/search/workflow tools
                mcp_servers=[mcp_server, bing_server],
                config={
                    "max_tokens": 8192,
                    **config
                }
            )

            # Stream the session
            agent_input = messages
            result = Runner.run_streamed(
                agent,
                input=agent_input,
                max_turns=30,
            )

            current_text = ''
            last_yield_length = 0
            tool_results: Dict[str, Dict[str, Any]] = {}
            tool_call_queue: List[str] = []
            workflow_update_ext = None  # collect workflow_update/param_update ext from tools

            async for event in result.stream_events():
                if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    delta_text = event.data.delta
                    if delta_text:
                        current_text += delta_text
                        if len(current_text) > last_yield_length:
                            last_yield_length = len(current_text)
                            yield (current_text, None)
                    continue

                if event.type == "run_item_stream_event":
                    if event.item.type == "tool_call_item":
                        tool_name = getattr(event.item.raw_item, 'name', 'unknown_tool')
                        tool_call_queue.append(tool_name)
                        log.info(f"[AllInOne] Tool called: {tool_name}")
                        continue

                    if event.item.type == "tool_call_output_item":
                        tool_output_data_str = str(event.item.output)
                        # Associate with FIFO queue
                        if tool_call_queue:
                            tool_name = tool_call_queue.pop(0)
                        else:
                            tool_name = 'unknown_tool'

                        # Try to parse output as JSON and capture ext
                        try:
                            import json
                            tool_output_data = json.loads(tool_output_data_str)
                            if "ext" in tool_output_data and tool_output_data["ext"]:
                                tool_ext_items = tool_output_data["ext"]
                                # capture any workflow_update/param_update; keep entire list
                                for ext_item in tool_ext_items:
                                    if ext_item.get("type") in ["workflow_update", "param_update"]:
                                        workflow_update_ext = tool_ext_items
                                        log.info(f"[AllInOne] Captured workflow-related ext from tool '{tool_name}'")
                                        break

                            if "text" in tool_output_data and tool_output_data.get('text'):
                                parsed_output = json.loads(tool_output_data['text'])
                                if isinstance(parsed_output, dict):
                                    answer = parsed_output.get("answer")
                                    data = parsed_output.get("data")
                                    tool_ext = parsed_output.get("ext")
                                else:
                                    answer = None
                                    data = parsed_output if isinstance(parsed_output, list) else None
                                    tool_ext = None

                                tool_results[tool_name] = {
                                    "answer": answer,
                                    "data": data,
                                    "ext": tool_ext,
                                    "content_dict": parsed_output
                                }
                        except Exception:
                            # Non-JSON output; store raw preview
                            tool_results[tool_name] = {
                                "answer": tool_output_data_str,
                                "data": None,
                                "ext": None,
                                "content_dict": None
                            }
                        continue

            # Post-stream processing: merge workflow tool results if present
            ext = None
            finished = True

            workflow_tools_found = [t for t in ["recall_workflow", "gen_workflow"] if t in tool_results]
            if workflow_tools_found:
                if "recall_workflow" in tool_results and "gen_workflow" in tool_results:
                    successful_workflows: List[Dict[str, Any]] = []
                    recall_result = tool_results["recall_workflow"]
                    gen_result = tool_results["gen_workflow"]
                    if recall_result.get("data"):
                        successful_workflows.extend(recall_result["data"])
                    if gen_result.get("data"):
                        # prioritize generated ones first
                        successful_workflows = list(gen_result["data"]) + successful_workflows

                    # de-duplicate by id
                    seen_ids = set()
                    unique_workflows = []
                    for wf in successful_workflows:
                        wf_id = wf.get('id')
                        if wf_id and wf_id not in seen_ids:
                            seen_ids.add(wf_id)
                            unique_workflows.append(wf)
                        elif not wf_id:
                            unique_workflows.append(wf)

                    if unique_workflows:
                        ext = [{"type": "workflow", "data": unique_workflows}]
                elif "gen_workflow" in tool_results:
                    gen_result = tool_results["gen_workflow"]
                    if gen_result.get("data"):
                        ext = [{"type": "workflow", "data": gen_result["data"]}]
                else:
                    # only recall_workflow was called; keep unfinished to encourage gen_workflow next time
                    ext = None
                    finished = False

            # Include any workflow_update/param_update ext captured during tool calls
            final_ext = ext
            if workflow_update_ext:
                if isinstance(workflow_update_ext, list):
                    final_ext = workflow_update_ext + (ext if ext else [])
                else:
                    final_ext = [workflow_update_ext] + (ext if ext else [])

            ext_with_finished = {"data": final_ext, "finished": finished}
            yield (current_text, ext_with_finished)

    except Exception as e:
        log.error(f"Error in all_in_one_invoke: {str(e)}")
        log.error(f"Traceback: {traceback.format_exc()}")
        error_message = f"I apologize, but an error occurred while processing your request: {str(e)}"
        yield (error_message, {"data": None, "finished": True})

'''
Author: ai-business-hql ai.bussiness.hql@gmail.com
Date: 2025-10-29 16:51:18
LastEditors: ai-business-hql ai.bussiness.hql@gmail.com
LastEditTime: 2025-10-29 17:01:17
FilePath: /ComfyUI-Copilot/backend/service/all_in_one_agent.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
