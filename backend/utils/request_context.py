"""
Request context management for ComfyUI Copilot
Uses contextvars to provide request-scoped context variables with async safety
"""

import contextvars
from typing import Optional, Dict, Any
from pydantic import BaseModel


class RewriteContext(BaseModel):
    rewrite_intent: str = ""
    current_workflow: str = ""
    node_infos: Optional[Dict[str, Any]] = None
    rewrite_expert: Optional[str] = ""

# Define context variables
_session_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('session_id', default=None)
_workflow_checkpoint_id: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar('workflow_checkpoint_id', default=None)
_config: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar('config', default=None)
_rewrite_context: contextvars.ContextVar[Optional[RewriteContext]] = contextvars.ContextVar('rewrite_context', default=None)


def set_session_id(session_id: str) -> None:
    """Set the session ID for the current request context"""
    _session_id.set(session_id)

def get_session_id() -> Optional[str]:
    """Get the session ID from the current request context"""
    return _session_id.get()

def set_workflow_checkpoint_id(checkpoint_id: Optional[int]) -> None:
    """Set the workflow checkpoint ID for the current request context"""
    _workflow_checkpoint_id.set(checkpoint_id)

def get_workflow_checkpoint_id() -> Optional[int]:
    """Get the workflow checkpoint ID from the current request context"""
    return _workflow_checkpoint_id.get()

def set_config(config: Dict[str, Any]) -> None:
    """Set the request config for the current request context"""
    _config.set(config)

def get_config() -> Optional[Dict[str, Any]]:
    """Get the request config from the current request context"""
    return _config.get()

def set_request_context(session_id: str, workflow_checkpoint_id: Optional[int] = None, config: Optional[Dict[str, Any]] = None) -> None:
    """Set all request context variables at once"""
    set_session_id(session_id)
    if workflow_checkpoint_id is not None:
        set_workflow_checkpoint_id(workflow_checkpoint_id)
    if config is not None:
        set_config(config)

def clear_request_context() -> None:
    """Clear all request context variables"""
    _session_id.set(None)
    _workflow_checkpoint_id.set(None)
    _config.set(None)

def set_rewrite_context(rewrite_context: RewriteContext) -> None:
    """Set the rewrite context for the current request context"""
    _rewrite_context.set(rewrite_context)

def get_rewrite_context() -> RewriteContext:
    """Get the rewrite context from the current request context"""
    context = _rewrite_context.get()
    if context is None:
        # 初始化一个新的 RewriteContext
        context = RewriteContext()
        _rewrite_context.set(context)
    return context