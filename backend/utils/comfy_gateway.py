"""
ComfyUI Gateway Utilities

This module provides Python implementations of ComfyUI API functions,
using HTTP requests to the ComfyUI server for consistency.
"""

import json
import os
import uuid
import logging
import asyncio
from typing import Dict, Any, Optional, List

# Import ComfyUI internal modules
import nodes
import execution
import folder_paths
import server
import aiohttp
from concurrent.futures import ThreadPoolExecutor, wait
from ..utils.logger import log

class ComfyGateway:
    """ComfyUI API Gateway for Python backend - uses internal functions instead of HTTP requests"""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize ComfyUI Gateway
        
        Args:
            base_url: Optional base URL for ComfyUI server. If not provided, will auto-detect.
        """
        # Get server instance for operations that need it
        self.server_instance = server.PromptServer.instance
        
        # Auto-detect server URL if not provided
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Auto-detect from server instance
            if hasattr(self.server_instance, 'address') and hasattr(self.server_instance, 'port'):
                address = self.server_instance.address or '127.0.0.1'
                port = self.server_instance.port or 8188
                # Use 127.0.0.1 for localhost to avoid potential connection issues
                if address in ['0.0.0.0', '::']:
                    address = '127.0.0.1'
                self.base_url = f"http://{address}:{port}"
            else:
                # Fallback to default
                self.base_url = "http://127.0.0.1:8188"
        
        logging.info(f"ComfyGateway initialized with base_url: {self.base_url}")

    async def run_prompt(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a prompt - HTTP call to ComfyUI /api/prompt endpoint
        
        This method sends an HTTP POST request to the ComfyUI server's /api/prompt endpoint
        to ensure consistent behavior and avoid code duplication.
        
        Args:
            json_data: The prompt/workflow data in the same format as HTTP API
            
        Returns:
            Dict containing the validation result, similar to HTTP API response
        """
        try:
            # Create a timeout configuration
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
            
            # Make HTTP request to /api/prompt endpoint
            url = f"{self.base_url}/api/prompt"
            headers = {
                'Content-Type': 'application/json'
            }
            

            # Create temporary session
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=json_data, headers=headers) as response:
                    response_data = await response.json()
                    status_code = response.status
            
            # Handle the response based on status code
            if status_code == 200:
                # Success response - add success flag for consistency
                return {
                    "success": True,
                    **response_data
                }
            else:
                # Error response (400, etc.) - add success flag for consistency
                return {
                    "success": False,
                    **response_data
                }
                
        except aiohttp.ClientConnectionError as e:
            logging.error(f"Connection error in run_prompt: {e}")
            return {
                "success": False,
                "error": {
                    "type": "connection_error",
                    "message": f"Failed to connect to ComfyUI server at {self.base_url}",
                    "details": str(e)
                },
                "node_errors": {}
            }
        except aiohttp.ClientTimeout as e:
            logging.error(f"Timeout error in run_prompt: {e}")
            return {
                "success": False,
                "error": {
                    "type": "timeout_error",
                    "message": "Request to ComfyUI server timed out",
                    "details": str(e)
                },
                "node_errors": {}
            }
        except Exception as e:
            logging.error(f"Error in run_prompt: {e}")
            return {
                "success": False,
                "error": {
                    "type": "internal_error",
                    "message": f"Internal error: {str(e)}",
                    "details": str(e)
                },
                "node_errors": {}
            }

    async def get_object_info(self, node_class: Optional[str] = None) -> Dict[str, Any]:
        """
        Get ComfyUI node definitions - HTTP call to ComfyUI /api/object_info endpoint
        
        Args:
            node_class: Optional specific node class to get info for
            
        Returns:
            Dict containing node definitions and their parameters
        """
        try:
            # Create a timeout configuration
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
            
            # Build URL - either specific node or all nodes
            if node_class:
                url = f"{self.base_url}/api/object_info/{node_class}"
            else:
                url = f"{self.base_url}/api/object_info"
            
            # Make HTTP request to /api/object_info endpoint
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logging.error(f"Failed to get object info: HTTP {response.status}")
                        return {}
                        
        except aiohttp.ClientConnectionError as e:
            logging.error(f"Connection error in get_object_info: {e}")
            return {}
        except aiohttp.ClientTimeout as e:
            logging.error(f"Timeout error in get_object_info: {e}")
            return {}
        except Exception as e:
            logging.error(f"Error getting object info: {e}")
            return {}

    async def get_installed_nodes(self) -> List[str]:
        """
        Get list of installed node types - HTTP call to ComfyUI /api/object_info endpoint
        
        Returns:
            List of installed node type names
        """
        try:
            object_info = await self.get_object_info()
            return list(object_info.keys())
        except Exception as e:
            logging.error(f"Error getting installed nodes: {e}")
            return []

    async def manage_queue(self, clear: bool = False, delete: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Clear the prompt queue or delete specific queue items - HTTP call to ComfyUI /api/queue endpoint
        
        Args:
            clear: If True, clears the entire queue
            delete: List of prompt IDs to delete from the queue
            
        Returns:
            Dict with the response from the queue management operation
        """
        try:
            # Create a timeout configuration
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
            
            # Prepare request data
            json_data = {}
            if clear:
                json_data["clear"] = True
            if delete:
                json_data["delete"] = delete
            
            # Make HTTP request to /api/queue endpoint
            url = f"{self.base_url}/api/queue"
            headers = {
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=json_data, headers=headers) as response:
                    if response.status == 200:
                        return {"success": True}
                    else:
                        logging.error(f"Failed to manage queue: HTTP {response.status}")
                        return {"error": f"HTTP {response.status}"}
                        
        except aiohttp.ClientConnectionError as e:
            logging.error(f"Connection error in manage_queue: {e}")
            return {"error": f"Connection error: {str(e)}"}
        except aiohttp.ClientTimeout as e:
            logging.error(f"Timeout error in manage_queue: {e}")
            return {"error": f"Timeout error: {str(e)}"}
        except Exception as e:
            logging.error(f"Error managing queue: {e}")
            return {"error": f"Failed to manage queue: {str(e)}"}

    async def interrupt_processing(self) -> Dict[str, Any]:
        """
        Interrupt the current processing/generation - HTTP call to ComfyUI /api/interrupt endpoint
        
        Returns:
            Dict with the response from the interrupt operation
        """
        try:
            # Create a timeout configuration
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
            
            # Make HTTP request to /api/interrupt endpoint
            url = f"{self.base_url}/api/interrupt"
            headers = {
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers) as response:
                    if response.status == 200:
                        return {"success": True}
                    else:
                        logging.error(f"Failed to interrupt processing: HTTP {response.status}")
                        return {"error": f"HTTP {response.status}"}
                        
        except aiohttp.ClientConnectionError as e:
            logging.error(f"Connection error in interrupt_processing: {e}")
            return {"error": f"Connection error: {str(e)}"}
        except aiohttp.ClientTimeout as e:
            logging.error(f"Timeout error in interrupt_processing: {e}")
            return {"error": f"Timeout error: {str(e)}"}
        except Exception as e:
            logging.error(f"Error interrupting processing: {e}")
            return {"error": f"Failed to interrupt processing: {str(e)}"}

    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """
        Get execution history for a specific prompt - HTTP call to ComfyUI /api/history/{prompt_id} endpoint
        
        Args:
            prompt_id: The ID of the prompt to get history for
            
        Returns:
            Dict containing the execution history and results
        """
        try:
            # Create a timeout configuration
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
            
            # Make HTTP request to /api/history/{prompt_id} endpoint
            url = f"{self.base_url}/api/history/{prompt_id}"
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logging.error(f"Failed to get history for prompt {prompt_id}: HTTP {response.status}")
                        return {"error": f"HTTP {response.status}"}
                        
        except aiohttp.ClientConnectionError as e:
            logging.error(f"Connection error in get_history: {e}")
            return {"error": f"Connection error: {str(e)}"}
        except aiohttp.ClientTimeout as e:
            logging.error(f"Timeout error in get_history: {e}")
            return {"error": f"Timeout error: {str(e)}"}
        except Exception as e:
            logging.error(f"Error fetching history for prompt {prompt_id}: {e}")
            return {"error": f"Failed to get history: {str(e)}"}

    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status - HTTP call to ComfyUI /api/queue endpoint
        
        Returns:
            Dict containing current queue information
        """
        try:
            # Create a timeout configuration
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
            
            # Make HTTP request to /api/queue endpoint
            url = f"{self.base_url}/api/queue"
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logging.error(f"Failed to get queue status: HTTP {response.status}")
                        return {"error": f"HTTP {response.status}"}
                        
        except aiohttp.ClientConnectionError as e:
            logging.error(f"Connection error in get_queue_status: {e}")
            return {"error": f"Connection error: {str(e)}"}
        except aiohttp.ClientTimeout as e:
            logging.error(f"Timeout error in get_queue_status: {e}")
            return {"error": f"Timeout error: {str(e)}"}
        except Exception as e:
            logging.error(f"Error getting queue status: {e}")
            return {"error": f"Failed to get queue status: {str(e)}"}


# Convenience functions for backward compatibility and easy importing
async def run_prompt(json_data: Dict[str, Any], base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Standalone function to run a prompt - HTTP call to ComfyUI /api/prompt endpoint
    
    Args:
        json_data: The prompt/workflow data to execute
        base_url: Optional base URL for ComfyUI server
        
    Returns:
        Dict containing the API response
    """
    gateway = ComfyGateway(base_url)
    return await gateway.run_prompt(json_data)

def node_info(node) -> Dict[str, Any]:
    info = {}
    info['name'] = node_class
    info['display_name'] = nodes.NODE_DISPLAY_NAME_MAPPINGS[node_class] if node_class in nodes.NODE_DISPLAY_NAME_MAPPINGS.keys() else node_class
    info['description'] = node['description'] if hasattr(node,'description') else ''
    info['python_module'] = getattr(node, "RELATIVE_PYTHON_MODULE", "nodes")
    info['category'] = node['category'] if hasattr(node, 'category') else 'sd'
    if hasattr(node, "input_types"):
        input_types = json.dumps(node['input_types'], ensure_ascii=False)
        if input_types:
            info['input'] = input_types
            info['input_order'] = {key: list(value.keys()) for (key, value) in input_types.items()}
        else: 
            info['input'] = {}
            info['input_order'] = []
    else: 
        info['input'] = {}
        info['input_order'] = []   

    if hasattr(node, "return_names"):
        info['output_name'] = json.dumps(node['return_names'], ensure_ascii=False)
    else:
        info['output_name'] = []

    if hasattr(node, "output_is_list"):
        info['output_is_list'] = node['output_is_list']
    else:
        info['output_is_list'] = [False] * len(info['output'])

    if hasattr(node, "output_name"):
        info['output_name'] = node['output_name']

    if hasattr(node, 'OUTPUT_NODE') and node['output_node'] == True:
        info['output_node'] = True
    else:
        info['output_node'] = False

    if hasattr(node, 'OUTPUT_TOOLTIPS'):
        info['output_tooltips'] = node['output_tooltips']

    if getattr(node, "DEPRECATED", False):
        info['deprecated'] = True
    if getattr(node, "EXPERIMENTAL", False):
        info['experimental'] = True

    if hasattr(node, 'API_NODE'):
        info['api_node'] = node['api_node']
    return info

async def get_version(node_class: str = None) -> str:
    try:
        # Create a timeout configuration
        timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
     
        # Build URL - either specific node or all nodes
        url = f"https://api.comfy.org/nodes/{node_class}/versions"
        
        # Make HTTP request to /api/object_info endpoint
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    versionData = result[0] if result[0] else None
                    version = versionData.get("version") if versionData.get("version") else None
                    return version
                else:
                    logging.error(f"Failed to get object info: HTTP {response.status}")
                    return None
                    
    except aiohttp.ClientConnectionError as e:
        logging.error(f"Connection error in get_object_info_from_comfyui_by_class: {e}")
        return None
    except aiohttp.ClientTimeout as e:
        logging.error(f"Timeout error in get_object_info_from_comfyui_by_class: {e}")
        return None
    except Exception as e:
        logging.error(f"Error getting get_object_info_from_comfyui_by_class: {e}")
        return None

async def get_object_info_from_comfyapi_by_class(node_class: str = None) -> Dict[str, Any]:
    """Standalone function to get object info from comfyapi by class - HTTP call to ComfyUI /api/object_info/{node_class} endpoint"""
    try:
        # Create a timeout configuration
        timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
     
        version = await get_version(node_class)

        # Build URL - either specific node or all nodes
        url = f"https://api.comfy.org/nodes/{node_class}/versions/{version}/comfy-nodes"
        
        # Make HTTP request to /api/object_info endpoint
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logging.error(f"Failed to get object info: HTTP {response.status}")
                    return {}
                    
    except aiohttp.ClientConnectionError as e:
        logging.error(f"Connection error in get_object_info_from_comfyui_by_class: {e}")
        return {}
    except aiohttp.ClientTimeout as e:
        logging.error(f"Timeout error in get_object_info_from_comfyui_by_class: {e}")
        return {}
    except Exception as e:
        logging.error(f"Error getting get_object_info_from_comfyui_by_class: {e}")
        return {}

async def get_object_info_by_missed_class_list(node_class_list: list[str] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    # Limit concurrency to avoid excessive outbound requests
    semaphore = asyncio.Semaphore(10)

    async def fetch_and_merge(node_class: str) -> None:
        async with semaphore:
            try:
                data = await get_object_info_from_comfyapi_by_class(node_class)
                if not isinstance(data, dict):
                    return

                # for d in data["comfy-nodes"]:
                     
                # Prefer exact key if present
                if node_class in data:
                    result[node_class] = data[node_class]
                    return

                # Otherwise, merge any matching requested keys from the payload
                for k, v in data.items():
                    if k in node_class_list and k not in result:
                        result[k] = v

                # Fallback: keep the whole payload under the class key if still missing
                if node_class not in result:
                    result[node_class] = data
            except Exception as e:
                logging.error(f"Error fetching object info for {node_class}: {e}")

    await asyncio.gather(*(fetch_and_merge(cls) for cls in node_class_list))
    return result

async def get_object_info_by_class_list(node_class_list: list[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """Get object info for a list of node classes.

    Strategy:
    - Fetch local object info once and take entries for classes that already exist.
    - For missing classes, concurrently fetch via get_object_info_from_comfyapi_by_class.
    - Merge results and return a dict keyed by class names.
    """
    # Start with whatever the local Comfy server knows
    local_object_info = await get_object_info(base_url) or {}

    if not node_class_list:
        return local_object_info

    result: Dict[str, Any] = {}
    for cls in node_class_list:
        if cls in local_object_info:
            result[cls] = local_object_info[cls]

    # Determine which classes we still need
    missing_classes = [cls for cls in node_class_list if cls not in result]
    log.info(f"get_object_info_by_class_list: node_class_list: {node_class_list}")
    log.info(f"get_object_info_by_class_list: missing_classes: {missing_classes}")
    if not missing_classes:
        return result

    result.update(await get_object_info_by_missed_class_list(missing_classes))
    return result

async def get_object_info(base_url: Optional[str] = None) -> Dict[str, Any]:
    """Standalone function to get object info - HTTP call to ComfyUI /api/object_info endpoint"""
    gateway = ComfyGateway(base_url)
    return await gateway.get_object_info()

async def get_object_info_by_class(node_class: str, base_url: Optional[str] = None) -> Dict[str, Any]:
    """Standalone function to get object info for specific node class - HTTP call to ComfyUI /api/object_info/{node_class} endpoint"""
    gateway = ComfyGateway(base_url)
    return await gateway.get_object_info(node_class)


async def get_installed_nodes(base_url: Optional[str] = None) -> List[str]:
    """Standalone function to get installed nodes - HTTP call to ComfyUI /api/object_info endpoint"""
    gateway = ComfyGateway(base_url)
    return await gateway.get_installed_nodes()

async def manage_queue(clear: bool = False, delete: Optional[List[str]] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """Standalone function to manage queue - HTTP call to ComfyUI /api/queue endpoint"""
    gateway = ComfyGateway(base_url)
    return await gateway.manage_queue(clear, delete)

async def interrupt_processing(base_url: Optional[str] = None) -> Dict[str, Any]:
    """Standalone function to interrupt processing - HTTP call to ComfyUI /api/interrupt endpoint"""
    gateway = ComfyGateway(base_url)
    return await gateway.interrupt_processing()

async def get_history(prompt_id: str, base_url: Optional[str] = None) -> Dict[str, Any]:
    """Standalone function to get history - HTTP call to ComfyUI /api/history/{prompt_id} endpoint"""
    gateway = ComfyGateway(base_url)
    return await gateway.get_history(prompt_id)

async def get_queue_status(base_url: Optional[str] = None) -> Dict[str, Any]:
    """Standalone function to get queue status - HTTP call to ComfyUI /api/queue endpoint"""
    gateway = ComfyGateway(base_url)
    return await gateway.get_queue_status()
