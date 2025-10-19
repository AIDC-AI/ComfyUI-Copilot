# Copyright (C) 2025 AIDC-AI
# Licensed under the MIT License.

"""
Authentication utilities for ComfyUI Copilot
"""

from typing import Optional
import uuid
from .globals import set_comfyui_copilot_api_key, get_comfyui_copilot_api_key, DISABLE_EXTERNAL_CONNECTIONS
from .logger import log

def extract_and_store_api_key(request) -> Optional[str]:
    """
    Extract Bearer token from Authorization header and store it in globals.
    In local-only mode (DISABLE_EXTERNAL_CONNECTIONS=true), generates a local UUID
    instead of requiring an external API key.
    
    Args:
        request: The aiohttp request object
        
    Returns:
        The extracted API key or generated UUID if successful, None otherwise
    """
    try:
        # In local-only mode, generate a local UUID for session management
        if DISABLE_EXTERNAL_CONNECTIONS:
            # Generate a local UUID (not a real API key, just for session identification)
            local_session_id = str(uuid.uuid4())
            set_comfyui_copilot_api_key(local_session_id)
            log.info(f"Local-only mode: Generated session UUID: {local_session_id[:12]}...")
            return local_session_id
        
        # External mode: extract API key from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            api_key = auth_header[7:]  # Remove 'Bearer ' prefix
            set_comfyui_copilot_api_key(api_key)
            log.info(f"ComfyUI Copilot API key extracted and stored: {api_key[:12]}...")
            
            # Verify it's stored correctly
            stored_key = get_comfyui_copilot_api_key()
            if stored_key == api_key:
                log.info("API key verification: ✓ Successfully stored in globals")
            else:
                log.error("API key verification: ✗ Storage failed")
                
            return api_key
        else:
            log.error("No valid Authorization header found in external mode")
            return None
    except Exception as e:
        log.error(f"Error in extract_and_store_api_key: {str(e)}")
        return None
