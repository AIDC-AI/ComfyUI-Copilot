# Implementation Plan: ComfyUI-Copilot Security Hardening

## Overview

Transform ComfyUI-Copilot from a cloud-dependent service to a privacy-focused, local-only AI assistant. This implementation removes all external server dependencies (except user-authorized Anthropic API for workflow operations) and prevents data exfiltration.

## Scope

This security hardening addresses critical vulnerabilities identified in the code review:
- External data transmission to comfyui-copilot-server.onrender.com
- API key exposure to third-party servers
- Telemetry/tracking without user consent
- Chinese model repository integration (ModelScope)
- No local-only operation mode

The solution enables completely local operation using the user's DGX Spark LLM at https://sparkle:13000/v1 with optional Anthropic integration for workflow operations.

## Types

### Configuration Types

```python
# backend/utils/globals.py
class SecurityConfig:
    """Security configuration for local-only operation"""
    LOCAL_LLM_BASE_URL: str = "https://sparkle:13000/v1"
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com/v1"
    DISABLE_EXTERNAL_CONNECTIONS: bool = True
    DISABLE_TELEMETRY: bool = True
    ALLOWED_MODEL_SOURCES: List[str] = ["huggingface", "civitai", "local"]
```

```python
# backend/utils/local_session_manager.py
class LocalSession:
    """Local session management without external server"""
    session_id: str  # UUID v4
    created_at: float
    last_activity: float
    workflow_checkpoints: List[int]
    config: Dict[str, Any]
```

### Model Source Types

```python
# backend/utils/model_sources.py
class ModelSource(Enum):
    HUGGINGFACE = "huggingface"
    CIVITAI = "civitai"
    LOCAL = "local"

class ModelInfo:
    """Unified model information across sources"""
    id: str
    name: str
    source: ModelSource
    download_url: Optional[str]
    local_path: Optional[str]
    size_bytes: Optional[int]
    description: str
```

## Files

### Files to Modify

#### Backend Configuration
- **backend/utils/globals.py**
  - Remove BACKEND_BASE_URL hardcoded default (`https://comfyui-copilot-server.onrender.com`)
  - Add LOCAL_LLM_BASE_URL configuration
  - Add DISABLE_EXTERNAL_CONNECTIONS flag
  - Add DISABLE_TELEMETRY flag
  - Update LLM_DEFAULT_BASE_URL to use local LLM
  - Add ANTHROPIC_BASE_URL for workflow operations

#### MCP Client
- **backend/service/mcp_client.py**
  - Remove MCPServerSse connection to external server
  - Remove external MCP endpoint: `BACKEND_BASE_URL + "/mcp-server/mcp"`
  - Disable external API key transmission in MCP headers
  - Implement local-only agent execution
  - Keep local tool execution capabilities

#### API Controllers
- **backend/controller/conversation_api.py**
  - Remove `track_event` endpoint entirely
  - Remove all trackEvent() calls
  - Remove upload_to_oss() function (external upload)
  - Remove external API key validation
  - Update agent invocation to use local LLM only
  - Implement local session storage

- **backend/controller/llm_api.py**
  - Update model listing to query local LLM endpoint
  - Remove external LLM server queries
  - Add support for Anthropic endpoint (workflow operations)

#### Authentication
- **backend/utils/auth_utils.py**
  - Remove extract_and_store_api_key (external API key handling)
  - Remove get_comfyui_copilot_api_key references
  - Implement local session token management
  - Add optional Anthropic API key validation (local storage only)

#### Agent Factory
- **backend/agent_factory.py**
  - Update agent creation to use local LLM configuration
  - Remove external MCP server dependencies
  - Configure agents for local-only execution

### Files to Delete

- **backend/utils/track_utils.py** - Telemetry utilities (if exists)
- **backend/utils/modelscope_gateway.py** - Chinese model repository integration

### Files to Create

#### Session Management
- **backend/utils/local_session_manager.py**
  - Implement UUID-based session generation
  - SQLite-based session storage
  - Session lifecycle management
  - Workflow checkpoint association

#### Model Sources
- **backend/utils/model_sources.py**
  - Abstract model source interface
  - Model source configuration

- **backend/utils/huggingface_gateway.py**
  - HuggingFace Hub API integration
  - Model search functionality
  - Download with huggingface_hub library
  - Local caching support

- **backend/utils/civitai_gateway.py**
  - Civitai API client
  - Model search and filtering
  - Download management
  - Rate limiting handling

- **backend/utils/local_model_scanner.py**
  - Scan ComfyUI model directories
  - Index existing models
  - Provide search across local models

#### Configuration
- **.env.local.template**
  - Environment variable template
  - Local LLM configuration
  - Anthropic API key (optional)
  - Security settings
  - Model source preferences

#### Documentation
- **SECURITY.md**
  - Security features documentation
  - Local-only operation guide
  - Privacy guarantees
  - Threat model

## Functions

### New Functions

#### backend/utils/local_session_manager.py
- `create_session() -> str` - Generate new UUID-based session
- `get_session(session_id: str) -> Optional[LocalSession]` - Retrieve session
- `update_session_activity(session_id: str) -> None` - Update last activity
- `cleanup_expired_sessions() -> int` - Remove old sessions
- `store_workflow_checkpoint(session_id: str, checkpoint_id: int) -> None`

#### backend/utils/huggingface_gateway.py
- `search_models(query: str, limit: int) -> List[ModelInfo]`
- `get_model_info(model_id: str) -> ModelInfo`
- `download_model(model_id: str, dest_dir: str) -> str`

#### backend/utils/civitai_gateway.py
- `search_models(query: str, limit: int) -> List[ModelInfo]`
- `get_model_info(model_id: int) -> ModelInfo`
- `download_model(model_id: int, dest_dir: str) -> str`

#### backend/utils/local_model_scanner.py
- `scan_model_directories() -> List[ModelInfo]`
- `search_local_models(query: str) -> List[ModelInfo]`
- `refresh_model_index() -> int`

### Modified Functions

#### backend/service/mcp_client.py
- `comfyui_agent_invoke()` - Remove external MCP connection, use local agents only

#### backend/controller/conversation_api.py
- `invoke_chat()` - Remove tracking, use local session management
- `upload_to_oss()` - DELETE (external upload)
- `download_model()` - Update to use new model sources

#### backend/utils/auth_utils.py
- `extract_and_store_api_key()` - DELETE
- `validate_anthropic_key(key: str) -> bool` - NEW (local validation)

### Removed Functions

#### backend/controller/conversation_api.py
- `trackEvent()` - DELETE (telemetry)
- `upload_to_oss()` - DELETE (external upload)

#### backend/utils/auth_utils.py
- `extract_and_store_api_key()` - DELETE
- `get_comfyui_copilot_api_key()` - DELETE (from globals)
- `set_comfyui_copilot_api_key()` - DELETE (from globals)

## Classes

### New Classes

#### backend/utils/local_session_manager.py
```python
class LocalSessionManager:
    """Manages user sessions locally without external server"""
    - __init__(db_path: str)
    - create_session() -> str
    - get_session(session_id: str) -> Optional[LocalSession]
    - update_activity(session_id: str) -> None
    - cleanup_expired(max_age_hours: int) -> int
```

#### backend/utils/model_sources.py
```python
class ModelSourceInterface(ABC):
    """Abstract interface for model sources"""
    - search_models(query: str, limit: int) -> List[ModelInfo]
    - get_model_info(model_id: str) -> ModelInfo
    - download_model(model_id: str, dest_dir: str) -> str

class HuggingFaceSource(ModelSourceInterface):
    """HuggingFace Hub model source"""

class CivitaiSource(ModelSourceInterface):
    """Civitai model source"""

class LocalSource(ModelSourceInterface):
    """Local filesystem model source"""
```

### Modified Classes

#### backend/utils/globals.py
- `GlobalState` - Add security configuration properties
  - `DISABLE_EXTERNAL_CONNECTIONS: bool`
  - `DISABLE_TELEMETRY: bool`
  - `LOCAL_LLM_BASE_URL: str`
  - `ANTHROPIC_BASE_URL: str`

### Removed Classes

- None (only function removals)

## Dependencies

### New Dependencies (requirements.txt)
```
# Model sources
huggingface-hub>=0.20.0
```

### Removed Dependencies
```
modelscope>=1.28.0  # REMOVE - Chinese model repository
```

### Updated Dependencies
- Keep: `openai>=1.5.0` (for OpenAI-compatible local LLM)
- Keep: `anthropic` (will be added for workflow operations - Phase 2)

## Testing

### Unit Tests to Create

#### test_local_session_manager.py
- Test session creation and retrieval
- Test session expiration
- Test concurrent session access
- Test checkpoint association

#### test_model_sources.py
- Test HuggingFace search and download
- Test Civitai search and download
- Test local model scanning
- Test model source fallback logic

#### test_security_isolation.py
- Verify no external connections (except allowed)
- Test blocked domains
- Validate local-only operation
- Test API key isolation

### Integration Tests

#### test_local_llm_integration.py
- Test connection to DGX Spark (https://sparkle:13000/v1)
- Test chat functionality with local LLM
- Test model listing from local LLM
- Test error handling for offline scenarios

#### test_workflow_with_anthropic.py
- Test workflow operations with Anthropic
- Test API key validation
- Test fallback to local LLM if Anthropic unavailable

### Existing Tests to Modify

- Update any tests that rely on external MCP server
- Update tests that expect external API key validation
- Update tests that use ModelScope integration

## Implementation Order

### Step 1: Create Configuration Infrastructure
1. Update `backend/utils/globals.py` with security flags
2. Create `.env.local.template` with configuration options
3. Add environment variable loading for security settings

### Step 2: Remove External Dependencies
4. Delete `backend/utils/modelscope_gateway.py`
5. Delete `backend/utils/track_utils.py` (if exists)
6. Remove all imports of deleted modules

### Step 3: Implement Local Session Management
7. Create `backend/utils/local_session_manager.py`
8. Implement SQLite session storage
9. Add session lifecycle management

### Step 4: Update MCP Client
10. Modify `backend/service/mcp_client.py` to disable external MCP
11. Remove external server connection code
12. Implement local-only agent execution

### Step 5: Update API Controllers
13. Modify `backend/controller/conversation_api.py`
    - Remove trackEvent endpoint and calls
    - Remove upload_to_oss function
    - Update to use local session manager
14. Modify `backend/controller/llm_api.py`
    - Update model listing to use local LLM
    - Add Anthropic endpoint support

### Step 6: Update Authentication
15. Modify `backend/utils/auth_utils.py`
    - Remove external API key handling
    - Implement local session tokens
16. Update `backend/agent_factory.py` for local configuration

### Step 7: Testing and Validation
17. Run unit tests for session management
18. Test local LLM integration with DGX Spark
19. Verify no external connections (network isolation test)
20. Validate all features work in local-only mode

### Step 8: Documentation
21. Create `SECURITY.md` with security features
22. Update `README.md` with local setup instructions
23. Document DGX Spark configuration
24. Document Anthropic integration for workflows
