"""
Agent Mode for ComfyUI-Copilot
Autonomous multi-step workflow planning, execution, and iteration.

Architecture:
    User Goal  →  Planner (decomposes into tasks)  →  Executor (runs each step)
                                                   →  Observer (checks results, loops)

Enhanced by Claude Opus 4.6
"""

import json
import asyncio
import traceback
from typing import List, Dict, Any, AsyncGenerator, Tuple, Optional

try:
    from agents import Agent, Runner, handoff, RunContextWrapper, HandoffInputData
    from agents.items import ItemHelpers
    from agents.run import Runner
    from agents.tool import function_tool
    from agents.mcp import MCPServerSse
    if not hasattr(__import__('agents'), 'Agent'):
        raise ImportError
except Exception:
    raise ImportError(
        "Detected incorrect or missing 'agents' package. "
        "Please install openai-agents:\n"
        "  python -m pip install -U openai-agents"
    )

from openai.types.responses import ResponseTextDeltaEvent
from openai import APIError

from ..agent_factory import create_agent
from ..utils.globals import (
    BACKEND_BASE_URL,
    WORKFLOW_MODEL_NAME,
    get_comfyui_copilot_api_key,
    get_language,
    DISABLE_WORKFLOW_GEN,
    detect_provider,
)
from ..utils.request_context import get_session_id, get_config
from ..utils.logger import log
from ..service.agent_mode_tools import (
    reset_task_queue,
    reset_tool_tracker,
    plan_tasks,
    update_task_status,
    get_plan_status,
    get_current_workflow_for_agent,
    save_workflow,
    validate_workflow,
    execute_workflow,
    check_execution_result,
    search_nodes,
    get_node_details,
    list_available_models,
)


# ---------------------------------------------------------------------------
# Null async context manager for optional MCP servers
# ---------------------------------------------------------------------------

class _NullCtx:
    """No-op async context manager used when an optional MCP server is skipped."""
    async def __aenter__(self):
        return self
    async def __aexit__(self, *exc):
        return False


# ---------------------------------------------------------------------------
# The Agent Mode orchestrator
# ---------------------------------------------------------------------------

async def agent_mode_invoke(
    messages: List[Dict[str, Any]],
    goal: str = "",
) -> AsyncGenerator[Tuple[str, Optional[Dict]], None]:
    """
    Run Agent Mode: an autonomous multi-step planner/executor.

    Yields (accumulated_text, ext_dict_or_none) tuples for streaming.
    """
    try:
        session_id = get_session_id()
        config = get_config()

        if not session_id:
            raise ValueError("No session_id found in request context")
        if not config:
            raise ValueError("No config found in request context")

        # Reset the task queue and tool tracker for this run
        reset_task_queue()
        reset_tool_tracker()

        # ---- Provider detection ----
        provider = detect_provider(
            (config or {}).get("openai_base_url", "") or ""
        )
        is_constrained = provider in ("groq", "lmstudio")

        # ---- Truncate messages to fit token budget ----
        # Groq free tier: 6K TPM (tokens per minute) including input + output.
        # Without MCP schemas, fixed overhead is ~650 tokens (prompt + 6 tool schemas).
        # Budget: 6000 - 650 - 1000 (output) = ~4350 tokens for messages.
        # For unconstrained providers with more headroom, use 6K budget.
        _MSG_TOKEN_BUDGET = 2000 if is_constrained else 6000
        messages = _truncate_messages(messages, _MSG_TOKEN_BUDGET)

        # ---- MCP servers ----
        # Constrained providers (Groq free tier, LMStudio): SKIP MCP entirely.
        # MCP tool schemas can be 2000-4000 tokens, which alone can exceed
        # Groq's 6K TPM limit.  Instead, the model builds workflows manually
        # using search_nodes + save_workflow with local tools only.
        #
        # Unconstrained providers (OpenAI, Anthropic): use MCP for
        # recall_workflow/gen_workflow which generate complete workflows.
        _MCP_TIMEOUT = 120.0
        _MCP_SESSION = 180.0

        mcp_server = None
        bing_server = None
        mcp_servers: list = []

        if not is_constrained:
            mcp_server = MCPServerSse(
                params={
                    "url": BACKEND_BASE_URL + "/mcp-server/mcp",
                    "timeout": _MCP_TIMEOUT,
                    "headers": {
                        "X-Session-Id": session_id,
                        "Authorization": f"Bearer {get_comfyui_copilot_api_key()}",
                    },
                },
                cache_tools_list=True,
                client_session_timeout_seconds=_MCP_SESSION,
            )
            bing_server = MCPServerSse(
                params={
                    "url": "https://mcp.api-inference.modelscope.net/8c9fe550938e4f/sse",
                    "timeout": _MCP_TIMEOUT,
                    "headers": {
                        "X-Session-Id": session_id,
                        "Authorization": f"Bearer {get_comfyui_copilot_api_key()}",
                    },
                },
                cache_tools_list=True,
                client_session_timeout_seconds=_MCP_SESSION,
            )
            mcp_servers = [mcp_server, bing_server]

        # Choose tool set based on provider capacity.
        if is_constrained:
            local_tools = [
                plan_tasks,
                get_current_workflow_for_agent,
                save_workflow,
                search_nodes,
                get_node_details,
                list_available_models,
            ]
        else:
            local_tools = [
                plan_tasks,
                update_task_status,
                get_plan_status,
                get_current_workflow_for_agent,
                save_workflow,
                validate_workflow,
                execute_workflow,
                check_execution_result,
                search_nodes,
                get_node_details,
                list_available_models,
            ]

        _ctx1 = mcp_server if mcp_server else _NullCtx()
        _ctx2 = bing_server if bing_server else _NullCtx()

        async with _ctx1, _ctx2:
            local_names = [getattr(t, "__name__", str(t)) for t in local_tools]
            log.info(
                f"[AgentMode] provider={provider}, constrained={is_constrained}, "
                f"local_tools={local_names}, mcp_servers={len(mcp_servers)}"
            )

            # ---- Build Agent Mode agent ----
            agent = create_agent(
                name="ComfyUI-Agent",
                instructions=_build_agent_instructions(is_constrained),
                mcp_servers=mcp_servers,
                tools=local_tools,
                config=config,
            )

            # ---- Stream the agent run ----
            result = Runner.run_streamed(
                agent,
                input=messages,
                max_turns=25,  # Enough for complex workflows, but prevents hour-long loops
            )

            current_text = ""
            last_yield_len = 0
            ext_data = None

            max_retries = 1   # reduced from 3 — SDK already retries once
            retry_count = 0

            # --- Loop / repetition detection ---
            _recent_tool_calls: list[str] = []  # track "tool:args" fingerprints
            _REPEAT_WINDOW = 8      # how many recent calls to remember
            _REPEAT_HARD_KILL = 3   # reduced from 5 — catch loops faster
            _tool_call_count = 0    # track total tool calls to detect hallucination
            _agent_start_time = asyncio.get_event_loop().time()
            # 5-minute hard timeout (down from 10).  The AsyncOpenAI client
            # now has a 120 s per-request timeout, so a hung tool call will
            # be interrupted much sooner.  This is the last-resort backstop.
            _AGENT_TIMEOUT_SECONDS = 300

            async def _process_events(stream):
                nonlocal current_text, last_yield_len, ext_data, _tool_call_count, _recent_tool_calls

                async for event in stream.stream_events():
                    # --- overall timeout check ---
                    elapsed = asyncio.get_event_loop().time() - _agent_start_time
                    if elapsed > _AGENT_TIMEOUT_SECONDS:
                        timeout_msg = (
                            f"\n\n⏱️ **Agent timed out** after {int(elapsed)}s. "
                            "Stopping to avoid wasting resources. "
                            "Please refine your request or install any missing nodes/models.\n"
                        )
                        current_text += timeout_msg
                        last_yield_len = len(current_text)
                        yield (current_text, None)
                        return  # stop processing events

                    # --- text deltas ---
                    if (
                        event.type == "raw_response_event"
                        and isinstance(event.data, ResponseTextDeltaEvent)
                    ):
                        delta = event.data.delta
                        if delta:
                            current_text += delta
                            if len(current_text) > last_yield_len:
                                last_yield_len = len(current_text)
                                yield (current_text, None)
                        continue

                    # --- agent handoffs ---
                    if event.type == "agent_updated_stream_event":
                        name = event.new_agent.name
                        log.info(f"[AgentMode] Handoff → {name}")
                        note = f"\n▸ **{name}**\n\n"
                        current_text += note
                        last_yield_len = len(current_text)
                        yield (current_text, None)
                        continue

                    # --- tool calls / outputs ---
                    if event.type == "run_item_stream_event":
                        if event.item.type == "tool_call_item":
                            tool_name = getattr(event.item.raw_item, "name", "unknown")
                            tool_args = getattr(event.item.raw_item, "arguments", "")
                            log.info(f"[AgentMode] Tool call: {tool_name}")
                            _tool_call_count += 1

                            # --- Warn if model uses info-only MCP tools ---
                            if tool_name in ("explain_node", "search_node"):
                                log.warning(
                                    f"[AgentMode] Model called info-only MCP tool '{tool_name}' — "
                                    "this does NOT place nodes on the canvas"
                                )

                            # --- Repetition detection with HARD KILL ---
                            fingerprint = f"{tool_name}:{tool_args}"
                            _recent_tool_calls.append(fingerprint)
                            if len(_recent_tool_calls) > _REPEAT_WINDOW:
                                _recent_tool_calls.pop(0)
                            repeat_count = _recent_tool_calls.count(fingerprint)
                            if repeat_count >= _REPEAT_HARD_KILL:
                                kill_msg = (
                                    f"\n\n🛑 **Agent stopped**: detected `{tool_name}` called {repeat_count} times "
                                    f"with identical arguments. The model is stuck in a loop.\n\n"
                                    "**What you can try:**\n"
                                    "- Rephrase your request with more specific details\n"
                                    "- Check if the required nodes/models are installed in ComfyUI\n"
                                    "- Try a different model in LMStudio (larger models follow instructions better)\n"
                                )
                                log.error(f"[AgentMode] HARD KILL: {tool_name} repeated {repeat_count}x — stopping agent")
                                current_text += kill_msg
                                last_yield_len = len(current_text)
                                yield (current_text, None)
                                return  # STOP the agent

                        elif event.item.type == "tool_call_output_item":
                            log.info(f"[AgentMode] Tool output received")
                            # Try to extract ext data (workflow updates etc.)
                            # When a tool like save_workflow returns an "ext" key,
                            # yield it immediately so the frontend can apply the
                            # workflow to the canvas in real time.
                            try:
                                out = json.loads(str(event.item.output))
                                if "ext" in out and out["ext"]:
                                    ext_data = out["ext"]
                                    # Yield immediately with ext data so the
                                    # frontend applies it to the canvas NOW
                                    yield (current_text, ext_data)
                            except (json.JSONDecodeError, TypeError):
                                pass
                        continue

            while retry_count <= max_retries:
                try:
                    async for chunk in _process_events(result):
                        yield chunk
                    break  # success
                except (AttributeError, TypeError, ConnectionError, OSError, APIError, TimeoutError, asyncio.TimeoutError, Exception) as e:
                    retry_count += 1
                    err = str(e)

                    # --- failed_generation: model couldn't produce valid tool call JSON ---
                    is_failed_gen = (
                        "failed_generation" in err.lower()
                        or "failed to call a function" in err.lower()
                    )
                    if is_failed_gen:
                        if retry_count <= max_retries:
                            # Retry once — Groq is probabilistic, often succeeds on second try
                            log.warning(f"[AgentMode] failed_generation (attempt {retry_count}/{max_retries}), retrying...")
                            await asyncio.sleep(1)
                            result = Runner.run_streamed(agent, input=messages, max_turns=25)
                            continue
                        failed_msg = (
                            "\n\n\u274c **Tool call failed** \u2014 the model couldn't generate valid function call JSON.\n\n"
                            "**Try:**\n"
                            "- Send the request again (may succeed on retry)\n"
                            "- Use a simpler, shorter request\n"
                            "- Try a different model (some handle tool calling better)\n"
                        )
                        log.error(f"[AgentMode] failed_generation: {err}")
                        current_text += failed_msg
                        yield (current_text, None)
                        break

                    # --- 413 / rate-limit: message too large or TPM exceeded ---
                    is_rate_limit = (
                        "413" in err or "rate_limit" in err.lower()
                        or "request too large" in err.lower()
                        or "tokens per minute" in err.lower()
                        or "429" in err
                    )
                    if is_rate_limit:
                        if retry_count <= max_retries:
                            # Wait for the rate limit window to reset, then retry
                            # with only the last user message (drop all history)
                            wait_msg = "\n\n⏳ Rate limit hit — waiting 30s before retrying with trimmed history...\n"
                            current_text += wait_msg
                            yield (current_text, None)
                            log.warning(f"[AgentMode] Rate limit hit (attempt {retry_count}), waiting 30s...")
                            await asyncio.sleep(30)
                            # Retry with only the last message
                            trimmed = [m for m in messages if True][-1:]
                            result = Runner.run_streamed(agent, input=trimmed, max_turns=25)
                            continue
                        rate_msg = (
                            "\n\n⚠️ **Rate limit exceeded** — the model's tokens-per-minute limit was hit twice.\n\n"
                            "**Try:**\n"
                            "- Wait a minute, then send the request again\n"
                            "- Start a **new** Agent Mode conversation (shorter history)\n"
                            "- Upgrade your Groq plan for higher TPM limits\n"
                        )
                        log.error(f"[AgentMode] Rate limit / 413: {err}")
                        current_text += rate_msg
                        yield (current_text, None)
                        break

                    # Detect timeout errors specifically — these usually mean
                    # LMStudio's tool-call SamplingSwitch hung.  Retrying the
                    # exact same request will hit the same wall, so give the
                    # user an actionable message instead of silently retrying.
                    is_timeout = isinstance(e, (TimeoutError, asyncio.TimeoutError)) or any(t in err.lower() for t in [
                        "timed out", "timeout", "read timeout", "clientrequest",
                    ])
                    if is_timeout:
                        timeout_hint = (
                            "\n\n⏱️ **Request timed out** while waiting for a response. "
                            "This can happen when the MCP server or LLM takes too long.\n\n"
                            "**Try:**\n"
                            "- Send the request again (may succeed on retry)\n"
                            "- Use a faster cloud model (e.g. Groq `llama-3.3-70b-versatile`)\n"
                            "- Simplify your request to fewer steps\n"
                            "- If using a local model, ensure it's not overloaded\n"
                        )
                        log.error(f"[AgentMode] Timeout detected: {err}")
                        current_text += timeout_hint
                        yield (current_text, None)
                        break  # don't retry timeouts

                    should_retry = any(
                        s in err
                        for s in [
                            "'NoneType' object has no attribute 'strip'",
                            "Connection broken",
                            "InvalidChunkLength",
                            "socket hang up",
                            "Connection reset",
                        ]
                    )
                    if should_retry and retry_count <= max_retries:
                        wait = min(2 ** (retry_count - 1), 10)
                        log.error(f"[AgentMode] Stream error (attempt {retry_count}/{max_retries}): {err}")
                        if current_text:
                            yield (current_text, None)
                        await asyncio.sleep(wait)
                        result = Runner.run_streamed(agent, input=messages, max_turns=25)
                    else:
                        raise

            # ---- Detect hallucination: agent produced text but called 0 tools ----
            if _tool_call_count == 0 and current_text.strip():
                hallucination_warning = (
                    "\n\n⚠️ **Warning**: The model responded without calling any tools. "
                    "It may have hallucinated results. "
                    "The workflow was **not** actually created or modified.\n\n"
                    "**Try:**\n"
                    "- Send your request again (the model may succeed on retry)\n"
                    "- Use a more capable model (e.g. `llama-3.3-70b-versatile` on Groq)\n"
                    "- Simplify/rephrase your request\n"
                )
                log.warning(f"[AgentMode] Hallucination detected: {len(current_text)} chars of text but 0 tool calls")
                current_text += hallucination_warning

            # ---- Final yield with ext data ----
            final_ext = None
            if ext_data:
                final_ext = {"data": ext_data, "finished": True}
            yield (current_text, final_ext)

    except Exception as e:
        err_str = str(e)
        log.error(f"[AgentMode] Fatal error: {e}\n{traceback.format_exc()}")

        # MCP / network timeout — show user-friendly retry suggestion
        is_mcp_timeout = isinstance(e, (TimeoutError, asyncio.TimeoutError)) or any(
            t in err_str.lower() for t in ["timed out", "clientrequest", "read timeout"]
        )
        is_rate_limit = (
            "413" in err_str or "rate_limit" in err_str.lower()
            or "request too large" in err_str.lower()
            or "tokens per minute" in err_str.lower()
        )
        if is_rate_limit:
            yield (
                "\n\n⚠️ **Request too large** for the model's token limit.\n\n"
                "**Try:**\n"
                "- Start a new Agent Mode conversation (shorter history)\n"
                "- Use a model with higher token limits\n"
                "- Upgrade your provider plan for higher TPM\n",
                None,
            )
        elif is_mcp_timeout:
            yield (
                "\n\n⏱️ **MCP server timed out** — the remote workflow service didn't respond in time.\n\n"
                "**Try:**\n"
                "- Send the request again (often succeeds on retry)\n"
                "- Use a simpler request\n"
                "- Check your internet connection\n",
                None,
            )
        # Groq-specific: model failed to generate valid tool call JSON
        elif "Failed to call a function" in err_str or "failed_generation" in err_str:
            yield (
                "\n\n❌ **Agent Mode Error**: The model failed to generate a valid tool call. "
                "This usually means the selected model struggles with tool/function calling.\n\n"
                "**Try:**\n"
                "- Switch to `llama-3.3-70b-versatile` (best for tool calling on Groq)\n"
                "- Simplify your request to fewer steps\n"
                "- Retry — sometimes the model succeeds on a second attempt\n",
                None,
            )
        # Schema validation error (shouldn't happen after fixes, but just in case)
        elif "'required' present but 'properties' is missing" in err_str:
            yield (
                "\n\n❌ **Agent Mode Error**: Tool schema validation failed. "
                "Please restart ComfyUI to pick up the latest fixes.\n",
                None,
            )
        else:
            yield (f"\n\n❌ **Agent Mode Error**: {err_str}", None)


# ---------------------------------------------------------------------------
# Message truncation — keep total message tokens under a budget
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    """Rough token count: ~3.5 chars per token for mixed English/JSON."""
    return max(1, int(len(text) / 3.5))


def _truncate_messages(messages: List[Dict[str, Any]], budget: int) -> List[Dict[str, Any]]:
    """
    Trim conversation history to fit within *budget* tokens.
    Strategy: always keep the last message (the user's goal), then add
    older messages newest-first until the budget is exhausted.
    """
    if not messages:
        return messages

    # Measure each message
    sized = []
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, list):  # multimodal content
            text = " ".join(
                p.get("text", "") for p in content if isinstance(p, dict)
            )
        else:
            text = str(content)
        sized.append((m, _estimate_tokens(text)))

    # Always keep the last message (current user goal)
    result = [sized[-1]]
    remaining = budget - sized[-1][1]

    # Walk backwards through earlier messages
    for msg, toks in reversed(sized[:-1]):
        if toks <= remaining:
            result.append((msg, toks))
            remaining -= toks
        else:
            # Try to include a truncated version (first 500 chars)
            content = msg.get("content", "")
            if isinstance(content, str) and len(content) > 500:
                truncated = {**msg, "content": content[:500] + "… [truncated]"}
                t_toks = _estimate_tokens(truncated["content"])
                if t_toks <= remaining:
                    result.append((truncated, t_toks))
                    remaining -= t_toks
            break  # budget exhausted

    # Restore chronological order
    result.reverse()
    return [m for m, _ in result]


# ---------------------------------------------------------------------------
# System prompt for the Agent Mode agent
# ---------------------------------------------------------------------------

def _build_agent_instructions(is_constrained: bool = False) -> str:
    lang = get_language()

    if is_constrained:
        # Minimal prompt for Groq/LMStudio — no MCP, model builds workflows
        # from scratch using search_nodes + get_node_details + save_workflow.
        return f"""You are ComfyUI Agent. You build COMPLETE multi-node workflows.

CRITICAL RULES:
- ONLY save_workflow places nodes. NEVER claim success without calling it.
- ALWAYS call search_nodes FIRST to find real class_type names. NEVER guess.
- ALWAYS call get_node_details to learn each node's inputs/outputs BEFORE building JSON.
- Build COMPLETE workflows: every workflow needs a source (loader), processing nodes, AND an output (SaveImage/PreviewImage).
- Use list_available_models to get REAL file names for model/checkpoint inputs.

STEPS (follow in order):
1. plan_tasks — decompose goal into steps
2. search_nodes — find the class_type for each node you need
3. get_node_details — learn required inputs, input types, and output types for each node
4. list_available_models — get real filenames for any model/checkpoint/lora inputs
5. Build COMPLETE workflow JSON connecting ALL nodes, then call save_workflow
6. Report result

WORKFLOW JSON FORMAT:
{{"node_id": {{"class_type": "ExactName", "inputs": {{...}}}}}}

CONNECTION RULES:
- To connect node outputs to inputs: use ["source_node_id", output_index]
- output_index is 0-based, matching the order from get_node_details RETURN_TYPES
- File/string inputs (ckpt_name, image filename) use plain strings, NOT connections
- Number inputs (width, seed, steps) use plain numbers, NOT strings

EXAMPLE — text-to-image (7 connected nodes, not 1):
{{"1":{{"class_type":"CheckpointLoaderSimple","inputs":{{"ckpt_name":"model.safetensors"}}}},
"2":{{"class_type":"CLIPTextEncode","inputs":{{"text":"a cat","clip":["1",1]}}}},
"3":{{"class_type":"CLIPTextEncode","inputs":{{"text":"ugly","clip":["1",1]}}}},
"4":{{"class_type":"EmptyLatentImage","inputs":{{"width":512,"height":512,"batch_size":1}}}},
"5":{{"class_type":"KSampler","inputs":{{"model":["1",0],"positive":["2",0],"negative":["3",0],"latent_image":["4",0],"seed":42,"steps":20,"cfg":7,"sampler_name":"euler","scheduler":"normal","denoise":1}}}},
"6":{{"class_type":"VAEDecode","inputs":{{"samples":["5",0],"vae":["1",2]}}}},
"7":{{"class_type":"SaveImage","inputs":{{"images":["6",0],"filename_prefix":"ComfyUI"}}}}}}

COMMON MISTAKES TO AVOID:
- Single-node workflows (WRONG: just one node. RIGHT: full pipeline with loader→process→output)
- Guessing class_type names (WRONG: "RestoreFormer". RIGHT: search first, use exact name from results)
- String values for connections (WRONG: "model.ckpt" for a MODEL input. RIGHT: ["1",0] connecting to a loader)
- Missing output node (ALWAYS end with SaveImage or PreviewImage)

Max 2 retries per tool. Respond in {lang}."""
    else:
        # Full prompt for unconstrained providers (OpenAI, Anthropic) with MCP
        return f"""You are ComfyUI Agent — you build ComfyUI workflows autonomously.

CANVAS RULE (CRITICAL):
- ONLY save_workflow places/modifies nodes on the canvas. No other tool modifies the canvas.
- explain_node and search_node are READ-ONLY info tools — they NEVER place or create anything.
- NEVER say "node added" or "workflow created" unless you called save_workflow and it returned success.

PIPELINE:
1. plan_tasks — decompose the goal
2. search_nodes / list_available_models — verify nodes & models exist
3. recall_workflow or gen_workflow (MCP) — generate workflow JSON
4. save_workflow(workflow_data=<JSON from step 3>) — THIS places it on canvas
5. validate_workflow — verify it works
6. Report to user

RULES:
- Call plan_tasks FIRST. Budget: ~15 tool calls.
- Pass MCP workflow JSON to save_workflow EXACTLY as received — no re-escaping.
- On error: fix once, then report. Max 2 same-tool calls with same args.
- If resource missing: STOP, tell user, suggest alternatives.
- Respond in {lang}.

JSON format: {{"node_id": {{"class_type": "Name", "inputs": {{...}}}}}}, connections: ["source_id", index]
"""
