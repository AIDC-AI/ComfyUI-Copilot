'''
Author: ai-business-hql qingli.hql@alibaba-inc.com
Date: 2025-08-08 17:14:52
LastEditors: ai-business-hql ai.bussiness.hql@gmail.com
LastEditTime: 2025-08-25 17:41:14
FilePath: /comfyui_copilot/backend/utils/globals.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''

"""
Global utilities for managing application-wide state and configuration.
"""

import threading
from typing import Optional, Dict, Any

class GlobalState:
    """Thread-safe global state manager for application-wide configuration."""
    
    def __init__(self):
        self._lock = threading.RLock()
        self._state: Dict[str, Any] = {
            'LANGUAGE': 'en',  # Default language
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a global state value."""
        with self._lock:
            return self._state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a global state value."""
        with self._lock:
            self._state[key] = value
    
    def get_language(self) -> str:
        """Get the current language setting."""
        return self.get('LANGUAGE', 'en')
    
    def set_language(self, language: str) -> None:
        """Set the current language setting."""
        self.set('LANGUAGE', language)
    
    def update(self, **kwargs) -> None:
        """Update multiple state values at once."""
        with self._lock:
            self._state.update(kwargs)
    
    def get_all(self) -> Dict[str, Any]:
        """Get a copy of all global state."""
        with self._lock:
            return self._state.copy()

# Global instance
_global_state = GlobalState()

# Convenience functions for external access
def get_global(key: str, default: Any = None) -> Any:
    """Get a global state value."""
    return _global_state.get(key, default)

def set_global(key: str, value: Any) -> None:
    """Set a global state value."""
    _global_state.set(key, value)

def get_language() -> str:
    """Get the current language setting."""
    language = _global_state.get_language()
    if not language:
        language = 'en'
    return language

def set_language(language: str) -> None:
    """Set the current language setting."""
    _global_state.set_language(language)

def update_globals(**kwargs) -> None:
    """Update multiple global values at once."""
    _global_state.update(**kwargs)

def get_all_globals() -> Dict[str, Any]:
    """Get a copy of all global state."""
    return _global_state.get_all()

def get_comfyui_copilot_api_key() -> Optional[str]:
    """Get the ComfyUI Copilot API key."""
    return _global_state.get('comfyui_copilot_api_key')

def set_comfyui_copilot_api_key(api_key: str) -> None:
    """Set the ComfyUI Copilot API key."""
    _global_state.set('comfyui_copilot_api_key', api_key)


BACKEND_BASE_URL = "https://comfyui-copilot-server.onrender.com"
LMSTUDIO_DEFAULT_BASE_URL = "http://localhost:1234/v1"
WORKFLOW_MODEL_NAME = "us.anthropic.claude-sonnet-4-20250514-v1:0"
# WORKFLOW_MODEL_NAME = "gpt-5-2025-08-07-GlobalStandard"
LLM_DEFAULT_BASE_URL = BACKEND_BASE_URL + "/v1"


def is_lmstudio_url(base_url: str) -> bool:
    """Check if the base URL is likely LMStudio based on common patterns."""
    if not base_url:
        return False
    
    base_url_lower = base_url.lower()
    # Common LMStudio patterns (supporting various ports and configurations)
    lmstudio_patterns = [
        "localhost:1234",        # Standard LMStudio port
        "127.0.0.1:1234", 
        "0.0.0.0:1234",
        ":1234/v1",
        "localhost:1235",        # Alternative port some users might use
        "127.0.0.1:1235", 
        "0.0.0.0:1235",
        ":1235/v1",
        "localhost/v1",          # Generic localhost patterns
        "127.0.0.1/v1"
    ]
    
    return any(pattern in base_url_lower for pattern in lmstudio_patterns)
