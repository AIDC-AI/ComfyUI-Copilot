'''
Author: ai-business-hql qingli.hql@alibaba-inc.com
Date: 2025-06-16 16:50:17
LastEditors: ai-business-hql ai.bussiness.hql@gmail.com
LastEditTime: 2025-11-17 15:09:44
FilePath: /comfyui_copilot/backend/service/mcp-client.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from ..utils.globals import BACKEND_BASE_URL, get_comfyui_copilot_api_key
from .. import core
import asyncio
import os
import traceback
from typing import List, Dict, Any, Optional

try:
    from agents._config import set_default_openai_api
    from agents.agent import Agent
    from agents.items import ItemHelpers
    from agents.mcp import MCPServerSse
    from agents.run import Runner
    from agents.tracing import set_tracing_disabled
    from agents import handoff, RunContextWrapper
    from agents.extensions import handoff_filters
    if not hasattr(__import__('agents'), 'Agent'):
        raise ImportError
except Exception:
    raise ImportError(
        "Detected incorrect or missing 'agents' package while loading MCP components. "
        "Please install 'openai-agents' and ensure this plugin prefers it. Commands:\n"
        "  python -m pip uninstall -y agents gym tensorflow\n"
        "  python -m pip install -U openai-agents"
    )

from ..agent_factory import create_agent
from ..service.workflow_rewrite_agent import create_workflow_rewrite_agent
from ..utils.request_context import get_rewrite_context, get_session_id, get_config
from ..utils.logger import log
from openai.types.responses import ResponseTextDeltaEvent
from openai import APIError, RateLimitError
from pydantic import BaseModel


class ImageData:
    """Image data structure to match reference implementation"""
    def __init__(self, filename: str, data: str, url: str = None):
        self.filename = filename
        self.data = data  # base64 data
        self.url = url    # uploaded URL

async def comfyui_agent_invoke(messages: List[Dict[str, Any]], images: List[ImageData] = None):
    """
    Invoke the ComfyUI agent with MCP tools and image support.
    
    This function mimics the behavior of the reference facade.py chat function,
    yielding (text, ext) tuples similar to the reference implementation.
    
    Args:
        messages: List of messages in OpenAI format [{"role": "user", "content": "..."}, ...]
        images: List of image data objects (optional)
        
    Yields:
        tuple: (text, ext) where text is accumulated text and ext is structured data
    """
    try:
        # Get session_id and config from request context
        session_id = get_session_id()
        config = get_config()
        
        if not session_id:
            raise ValueError("No session_id found in request context")
        if not config:
            raise ValueError("No config found in request context")
        
        # Create MCP server instances
        mcp_server = MCPServerSse(
            params= {
                "url": BACKEND_BASE_URL + "/mcp-server/mcp",
                "timeout": 300.0,
                "headers": {"X-Session-Id": session_id, "Authorization": f"Bearer {get_comfyui_copilot_api_key()}"}
            },
            cache_tools_list=True,
            client_session_timeout_seconds=300.0
        )
        
        bing_server = MCPServerSse(
            params= {
                "url": "https://mcp.api-inference.modelscope.net/8c9fe550938e4f/sse",
                "timeout": 300.0,
                "headers": {"X-Session-Id": session_id, "Authorization": f"Bearer {get_comfyui_copilot_api_key()}"}
            },
            cache_tools_list=True,
            client_session_timeout_seconds=300.0
        )
        
        server_list = [mcp_server, bing_server]
        
        async with mcp_server, bing_server:
            
            # 创建workflow_rewrite_agent实例 (session_id通过context获取)
            workflow_rewrite_agent_instance = create_workflow_rewrite_agent()
            
            class HandoffRewriteData(BaseModel):
                latest_rewrite_intent: str
            
            async def on_handoff(ctx: RunContextWrapper[None], input_data: HandoffRewriteData):
                get_rewrite_context().rewrite_intent = input_data.latest_rewrite_intent
                log.info(f"Rewrite agent called with intent: {input_data.latest_rewrite_intent}")
            
            handoff_rewrite = handoff(
                agent=workflow_rewrite_agent_instance,
                input_type=HandoffRewriteData,
                input_filter=handoff_filters.remove_all_tools,
                on_handoff=on_handoff,
            )
            
            agent = create_agent(
                name="ComfyUI-Copilot",
                instructions=f"""You are a powerful AI assistant for designing image processing workflows, capable of automating problem-solving using tools and commands.

When handing off to workflow rewrite agent or other agents, this session ID should be used for workflow data management.

You must adhere to the following constraints to complete the task:

- [Important!] Respond must in the language used by the user in their question. Regardless of the language returned by the tools being called, please return the results based on the language used in the user's query. For example, if user ask by English, you must return
- Ensure that the commands or tools you invoke are within the provided tool list.
- If the execution of a command or tool fails, try changing the parameters or their format before attempting again.
- Your generated responses must follow the factual information given above. Do not make up information.
- If the result obtained is incorrect, try rephrasing your approach.
- Do not query for already obtained information repeatedly. If you successfully invoked a tool and obtained relevant information, carefully confirm whether you need to invoke it again.
- Ensure that the actions you generate can be executed accurately. Actions may include specific methods and target outputs.
- When you encounter a concept, try to obtain its precise definition and analyze what inputs can yield specific values for it.
- When generating a natural language query, include all known information in the query.
- Before performing any analysis or calculation, ensure that all sub-concepts involved have been defined.
- Printing the entire content of a file is strictly prohibited, as such actions have high costs and can lead to unforeseen consequences.
- Ensure that when you call a tool, you have obtained all the input variables for that tool, and do not fabricate any input values for it.
- Respond with markdown, using a minimum of 3 heading levels (H3, H4, H5...), and when including images use the format ![alt text](url),
- [Critical!] When the user's intent is to get workflows or generate images with specific requirements, you MUST ALWAYS call BOTH recall_workflow tool AND gen_workflow tool to provide comprehensive workflow options. Never call just one of these tools - both are required for complete workflow assistance. First call recall_workflow to find existing similar workflows, then call gen_workflow to generate new workflow options.
- When the user's intent is to query, return the query result directly without attempting to assist the user in performing operations.
- When the user's intent is to get prompts for image generation (like Stable Diffusion). Use specific descriptive language with proper weight modifiers (e.g., (word:1.2)), prefer English terms, and separate elements with commas. Include quality terms (high quality, detailed), style specifications (realistic, anime), lighting (cinematic, golden hour), and composition (wide shot, close up) as needed. When appropriate, include negative prompts to exclude unwanted elements. Return words divided by commas directly without any additional text.
- If you cannot find the information needed to answer a query, consider using bing_search to obtain relevant information. For example, if search_node tool cannot find the node, you can use bing_search to obtain relevant information about those nodes or components.
- If search_node tool cannot find the node, you MUST use bing_search to obtain relevant information about those nodes or components.

- **DEBUG Intent** - When the user's intent is to debug workflow execution problems, runtime errors, or troubleshoot failed workflows (keywords: "debug", "调试", "工作流报错", "执行失败", "workflow failed", "node error", "runtime error", "不能运行", "出错了"), respond with: "Please click the 🪲 button in the bottom right corner to trigger debug"

- **WORKFLOW REWRITE Intent** - [Critical!] When the user's intent is to functionally modify, enhance, or add NEW features to the current workflow OR modify the current canvas (keywords: "修改当前工作流", "更新工作流", "在当前工作流中添加", "添加功能", "enhance current workflow", "modify workflow", "add to current workflow", "update current workflow", "添加LoRA", "加个upscale", "add upscaling", "修改当前画布", "更新画布", "在画布中", "modify current canvas", "update canvas", "change canvas"), you MUST handoff to the Workflow Rewrite Agent immediately. This is for feature enhancements, not error fixes.

- **ERROR MESSAGE ANALYSIS** - When a user pastes specific error text/logs (containing terms like "Failed", "Error", "Traceback", or stack traces), prioritize providing troubleshooting help rather than invoking search tools. Follow these steps:
  1. Analyze the error to identify the root cause (error type, affected component, missing dependencies, etc.)
  2. Explain the issue in simple terms
  3. Provide concrete, executable solutions including:
     - Specific shell commands to fix the issue (e.g., `git pull`, `pip install`, file path corrections)
     - Code snippets if applicable
     - Configuration file changes with exact paths and values
  4. If the error relates to a specific ComfyUI extension or node, include instructions for:
     - Updating the extension (`cd path/to/extension && git pull`)
     - Reinstalling dependencies
     - Alternative approaches if the extension is problematic
                """,
                mcp_servers=server_list,
                handoffs=[handoff_rewrite],
                config=config
            )

            # Use messages directly as agent input since they're already in OpenAI format
            # The caller has already handled image formatting within messages
            agent_input = messages
            log.info(f"-- Processing {len(messages)} messages")

            result = Runner.run_streamed(
                agent,
                input=agent_input,
                max_turns=30,
            )
            log.info("=== MCP Agent Run starting ===")
            
            # Variables to track response state similar to reference facade.py
            current_text = ''
            ext = None
            tool_results = {}  # Store results from different tools
            workflow_tools_called = set()  # Track called workflow tools
            last_yield_length = 0
            tool_call_queue = []  # Queue to track tool calls in order
            current_tool_call = None  # Track current tool being called
            # Collect workflow update ext data from tools and message outputs
            workflow_update_ext = None
            # Track if we've seen any handoffs to avoid showing initial handoff
            handoff_occurred = False
            
            # Enhanced retry mechanism for OpenAI streaming errors
            max_retries = 3
            retry_count = 0
            
            async def process_stream_events(stream_result):
                """Process stream events with enhanced error handling"""
                nonlocal current_text, last_yield_length, tool_call_queue, workflow_update_ext, tool_results, workflow_tools_called, handoff_occurred
                
                try:
                    async for event in stream_result.stream_events():
                        # Handle different event types similar to reference implementation
                        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                            # Stream text deltas for real-time response
                            delta_text = event.data.delta
                            if delta_text:
                                current_text += delta_text
                                # Yield tuple (accumulated_text, None) for streaming - similar to facade.py
                                # Only yield if we have new content to avoid duplicate yields
                                if len(current_text) > last_yield_length:
                                    last_yield_length = len(current_text)
                                    yield (current_text, None)
                            continue
                            
                        elif event.type == "agent_updated_stream_event":
                            new_agent_name = event.new_agent.name
                            log.info(f"Handoff to: {new_agent_name}")
                            
                            # Only show handoff message if we've already seen handoffs
                            # This prevents showing the initial handoff to ComfyUI-Copilot
                            if handoff_occurred:
                                # Add handoff information to the stream
                                handoff_text = f"\n▸ **Switching to {new_agent_name}**\n\n"
                                current_text += handoff_text
                                last_yield_length = len(current_text)
                                
                                # Yield text update only
                                yield (current_text, None)
                            
                            # Mark that we've seen a handoff
                            handoff_occurred = True
                            continue
                            
                        elif event.type == "run_item_stream_event":
                            if event.item.type == "tool_call_item":
                                # Get tool name correctly using raw_item.name
                                tool_name = getattr(event.item.raw_item, 'name', 'unknown_tool')
                                # Add to queue instead of overwriting current_tool_call
                                tool_call_queue.append(tool_name)
                                log.info(f"-- Tool '{tool_name}' was called")
                                
                                # Track workflow tools being called
                                if tool_name in ["recall_workflow", "gen_workflow"]:
                                    workflow_tools_called.add(tool_name)
                            elif event.item.type == "tool_call_output_item":
                                log.info(f"-- Tool output: {event.item.output}")
                                # Store tool output for potential ext data processing
                                tool_output_data_str = str(event.item.output)
                                
                                # Get the next tool from the queue (FIFO)
                                if tool_call_queue:
                                    tool_name = tool_call_queue.pop(0)
                                    log.info(f"-- Associating output with tool '{tool_name}'")
                                else:
                                    tool_name = 'unknown_tool'
                                    log.info(f"-- Warning: No tool call in queue for output")
                                
                                try:
                                    import json
                                    tool_output_data = json.loads(tool_output_data_str)
                                    if "ext" in tool_output_data and tool_output_data["ext"]:
                                        # Store all ext items from tool output, not just workflow_update
                                        tool_ext_items = tool_output_data["ext"]
                                        for ext_item in tool_ext_items:
                                            if ext_item.get("type") == "workflow_update" or ext_item.get("type") == "param_update":
                                                workflow_update_ext = tool_ext_items  # Store all ext items, not just one
                                                log.info(f"-- Captured workflow tool ext from tool output: {len(tool_ext_items)} items")
                                                break
                                        
                                    if "text" in tool_output_data and tool_output_data.get('text'):
                                        parsed_output = json.loads(tool_output_data['text'])
                                        
                                        # Handle case where parsed_output might be a list instead of dict
                                        if isinstance(parsed_output, dict):
                                            answer = parsed_output.get("answer")
                                            data = parsed_output.get("data")
                                            tool_ext = parsed_output.get("ext")
                                        else:
                                            # If it's a list or other type, handle gracefully
                                            answer = None
                                            data = parsed_output if isinstance(parsed_output, list) else None
                                            tool_ext = None
                                        
                                        # Store tool results similar to reference facade.py
                                        tool_results[tool_name] = {
                                            "answer": answer,
                                            "data": data,
                                            "ext": tool_ext,
                                            "content_dict": parsed_output
                                        }
                                        log.info(f"-- Stored result for tool '{tool_name}': data={len(data) if data else 0}, ext={tool_ext}")
                                        
                                        # Track workflow tools that produced results
                                        if tool_name in ["recall_workflow", "gen_workflow"]:
                                            log.info(f"-- Workflow tool '{tool_name}' produced result with data: {len(data) if data else 0}")
                                        
                                        
                                        
                                except (json.JSONDecodeError, TypeError) as e:
                                    # If not JSON or parsing fails, treat as regular text
                                    log.error(f"-- Failed to parse tool output as JSON: {e}")
                                    log.error(f"-- Traceback: {traceback.format_exc()}")
                                    tool_results[tool_name] = {
                                        "answer": tool_output_data_str,
                                        "data": None,
                                        "ext": None,
                                        "content_dict": None
                                    }
                                
                            elif event.item.type == "message_output_item":
                                pass
                            else:
                                pass  # Ignore other event types
                                
                except Exception as e:
                    log.error(f"Unexpected streaming error: {e}")
                    log.error(f"Traceback: {traceback.format_exc()}")
                    raise e
            
            # Implement retry mechanism with exponential backoff
            while retry_count <= max_retries:
                try:
                    async for stream_data in process_stream_events(result):
                        if stream_data:
                            yield stream_data
                    # If we get here, streaming completed successfully
                    break
                    
                except (AttributeError, TypeError, ConnectionError, OSError, APIError) as stream_error:
                    retry_count += 1
                    error_msg = str(stream_error)
                    
                    # Check for specific streaming errors that are worth retrying
                    should_retry = (
                        "'NoneType' object has no attribute 'strip'" in error_msg or
                        "Connection broken" in error_msg or
                        "InvalidChunkLength" in error_msg or
                        "socket hang up" in error_msg or
                        "Connection reset" in error_msg
                    )
                    
                    if should_retry and retry_count <= max_retries:
                        wait_time = min(2 ** (retry_count - 1), 10)  # Exponential backoff, max 10 seconds
                        log.error(f"Stream error (attempt {retry_count}/{max_retries}): {error_msg}")
                        log.info(f"Retrying in {wait_time} seconds...")
                        
                        # Yield current progress before retry
                        if current_text:
                            yield (current_text, None)
                        
                        await asyncio.sleep(wait_time)
                        
                        try:
                            # Create a new result object for retry
                            result = Runner.run_streamed(
                                agent,
                                input=agent_input,
                            )
                            log.info(f"=== Retry attempt {retry_count} starting ===")
                        except Exception as retry_setup_error:
                            log.error(f"Failed to setup retry: {retry_setup_error}")
                            if retry_count >= max_retries:
                                raise stream_error  # Re-raise original error if max retries reached
                            continue
                    else:
                        log.error(f"Non-retryable streaming error or max retries reached: {error_msg}")
                        log.error(f"Traceback: {traceback.format_exc()}")
                        if isinstance(stream_error, RateLimitError):
                            default_error_msg = 'Rate limit exceeded, please try again later.'
                            error_body = stream_error.body
                            error_msg = error_body['message'] if error_body and 'message' in error_body else None
                            final_error_msg = error_msg or default_error_msg
                            yield (final_error_msg, None)
                            return
                        else:
                            # Continue to normal processing, error will be handled by outer try-catch
                            break
                        
                except Exception as unexpected_error:
                    retry_count += 1
                    log.error(f"Unexpected error during streaming (attempt {retry_count}/{max_retries}): {unexpected_error}")
                    log.error(f"Traceback: {traceback.format_exc()}")
                    
                    if retry_count > max_retries:
                        log.error("Max retries exceeded for unexpected error")
                        break
                    else:
                        # Brief wait before retry for unexpected errors
                        await asyncio.sleep(1)
                        continue

            # Add detailed debugging info about tool results
            log.info(f"Total tool results: {len(tool_results)}")
            for tool_name, result in tool_results.items():
                result_type = "Message Output" if tool_name == '_message_output_ext' else "Tool"
                log.info(f"{result_type}: {tool_name}")
                log.info(f"  - Has data: {result['data'] is not None}")
                log.info(f"  - Data length: {len(result['data']) if result['data'] else 0}")
                log.info(f"  - Has ext: {result['ext'] is not None}")
                if result['ext']:
                    log.info(f"  - Ext types: {[item.get('type') for item in (result['ext'] if isinstance(result['ext'], list) else [result['ext']])]}")
                log.info(f"  - Answer preview: {result['answer'][:100] if result['answer'] else 'None'}...")
            log.info(f"=== End Tool Results Summary ===\n")

            # Process workflow tools results integration similar to reference facade.py
            workflow_tools_found = [tool for tool in ["recall_workflow", "gen_workflow"] if tool in tool_results]
            finished = False  # Default finished state

            if workflow_tools_found:
                log.info(f"Workflow tools called: {workflow_tools_found}")
                
                # Check if both workflow tools were called
                if "recall_workflow" in tool_results and "gen_workflow" in tool_results:
                    log.info("Both recall_workflow and gen_workflow were called, merging results")
                    
                    # Check each tool's success and merge results
                    successful_workflows = []

                    recall_result = tool_results["recall_workflow"]
                    if recall_result["data"] and len(recall_result["data"]) > 0:
                        log.info(f"recall_workflow succeeded with {len(recall_result['data'])} workflows")
                        log.info(f"  - Workflow IDs: {[w.get('id') for w in recall_result['data']]}")
                        successful_workflows.extend(recall_result["data"])
                    else:
                        log.error("recall_workflow failed or returned no data")

                    gen_result = tool_results["gen_workflow"]
                    if gen_result["data"] and len(gen_result["data"]) > 0:
                        log.info(f"gen_workflow succeeded with {len(gen_result['data'])} workflows")
                        log.info(f"  - Workflow IDs: {[w.get('id') for w in gen_result['data']]}")
                        successful_workflows.insert(0, *gen_result["data"])
                    else:
                        log.error("gen_workflow failed or returned no data")

                    # Remove duplicates based on workflow ID
                    seen_ids = set()
                    unique_workflows = []
                    for workflow in successful_workflows:
                        workflow_id = workflow.get('id')
                        if workflow_id and workflow_id not in seen_ids:
                            seen_ids.add(workflow_id)
                            unique_workflows.append(workflow)
                            log.info(f"  - Added unique workflow: {workflow_id} - {workflow.get('name', 'Unknown')}")
                        elif workflow_id:
                            log.info(f"  - Skipped duplicate workflow: {workflow_id} - {workflow.get('name', 'Unknown')}")
                        else:
                            # If no ID, add anyway (shouldn't happen but just in case)
                            unique_workflows.append(workflow)
                            log.info(f"  - Added workflow without ID: {workflow.get('name', 'Unknown')}")

                    log.info(f"Total workflows before deduplication: {len(successful_workflows)}")
                    log.info(f"Total workflows after deduplication: {len(unique_workflows)}")

                    # Create final ext structure
                    if unique_workflows:
                        ext = [{
                            "type": "workflow",
                            "data": unique_workflows
                        }]
                        log.info(f"Returning {len(unique_workflows)} workflows from successful tools")
                    else:
                        ext = None
                        log.error("No successful workflow data to return")
                    
                    # Both tools called, finished = True
                    finished = True
                        
                elif "recall_workflow" in tool_results and "gen_workflow" not in tool_results:
                    # Only recall_workflow was called, don't return ext, keep finished=false
                    log.info("Only recall_workflow was called, waiting for gen_workflow, not returning ext")
                    ext = None
                    finished = False  # This is the key: keep finished=false to wait for gen_workflow
                    
                elif "gen_workflow" in tool_results and "recall_workflow" not in tool_results:
                    # Only gen_workflow was called, return its result normally
                    log.info("Only gen_workflow was called, returning its result")
                    gen_result = tool_results["gen_workflow"]
                    if gen_result["data"] and len(gen_result["data"]) > 0:
                        ext = [{
                            "type": "workflow",
                            "data": gen_result["data"]
                        }]
                        log.info(f"Returning {len(gen_result['data'])} workflows from gen_workflow")
                    else:
                        ext = None
                        log.error("gen_workflow failed or returned no data")
                    
                    # Only gen_workflow called, finished = True
                    finished = True
            else:
                # No workflow tools called, check if other tools or message output returned ext
                for tool_name, result in tool_results.items():
                    if result["ext"]:
                        ext = result["ext"]
                        log.info(f"Using ext from {tool_name}")
                        break
                
                # When no workflow tools are called (e.g., handoff to workflow_rewrite_agent)
                # The agent stream has completed at this point, so finished should be True
                # The workflow_update_ext will be included in final_ext regardless
                finished = True
            
            
            # Prepare final ext (debug_ext would be empty here since no debug events)
            final_ext = ext
            if workflow_update_ext:
                # workflow_update_ext is now a list of ext items, so extend rather than wrap
                if isinstance(workflow_update_ext, list):
                    final_ext = workflow_update_ext + (ext if ext else [])
                else:
                    # Backward compatibility: if it's a single item, wrap it
                    final_ext = [workflow_update_ext] + (ext if ext else [])
                log.info(f"-- Including workflow_update ext in final response: {len(workflow_update_ext) if isinstance(workflow_update_ext, list) else 1} items")
            
            # Final yield with complete text, ext data, and finished status
            # Return as tuple (text, ext_with_finished) where ext_with_finished includes finished info
            if final_ext:
                # Add finished status to ext structure
                ext_with_finished = {
                    "data": final_ext,
                    "finished": finished
                }
            else:
                ext_with_finished = {
                    "data": None,
                    "finished": finished
                }
            
            yield (current_text, ext_with_finished)
            
    except Exception as e:
        log.error(f"Error in comfyui_agent_invoke: {str(e)}")
        log.error(f"Traceback: {traceback.format_exc()}")
        error_message = f"I apologize, but an error occurred while processing your request: {str(e)}"
        
        # Check if this is a retryable streaming error that should not finish the conversation
        error_msg = str(e)
        is_retryable_streaming_error = (
            "'NoneType' object has no attribute 'strip'" in error_msg or
            "Connection broken" in error_msg or
            "InvalidChunkLength" in error_msg or
            "socket hang up" in error_msg or
            "Connection reset" in error_msg or
            isinstance(e, APIError)
        )
        
        if is_retryable_streaming_error:
            # For retryable streaming errors, don't finish - allow user to retry
            log.info(f"Detected retryable streaming error, setting finished=False to allow retry")
            error_ext = {
                "data": None,
                "finished": False
            }
            error_message = f"A temporary streaming error occurred: {str(e)}. Please try your request again."
        else:
            # For other errors, finish the conversation
            error_ext = {
                "data": None,
                "finished": True
            }
        
        yield (error_message, error_ext)
