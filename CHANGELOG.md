# Changelog

All notable changes to this fork of ComfyUI-Copilot are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2025-01-XX

This is a major enhancement release that adds autonomous agent capabilities, multi-provider support, voice I/O, and fixes critical LM Studio integration issues.

### Added

#### Agent Mode - Autonomous Workflow Building
- **PLAN/EXECUTE/VALIDATE/REPORT Loop** (`backend/service/agent_mode.py`)
  - Agent breaks down complex goals into discrete tasks
  - Autonomously searches nodes, builds workflows, sets parameters
  - Validates workflow integrity before presenting to user
  - Provides step-by-step progress reporting
  
- **Tool Budget System** (`backend/service/agent_mode_tools.py`)
  - Per-tool call limits (e.g., `search_nodes` max 4x, `save_workflow` max 5x)
  - Global tool budget of 30 calls per agent session
  - Loop prevention: kills if same tool+args repeated 3x in last 8 calls
  - 5-minute total timeout, 25 max agent turns
  
- **Visual Progress Tracking** (`ui/src/components/chat/AgentModeIndicator.tsx`)
  - Real-time step indicator showing current agent phase
  - Task queue visualization
  - Toggle with robot button in chat input

#### Multi-Provider Support
- **OpenAI-Compatible Provider Architecture** (`backend/utils/globals.py`)
  - `detect_provider()` function with URL pattern matching
  - Provider-specific constants: timeouts, token limits, features
  
- **Supported Providers**:
  - **OpenAI**: Full feature support with default model `gemini-2.5-flash`
  - **Groq**: Free tier with `llama-3.3-70b-versatile`, reduced tool sets for rate limits
  - **Anthropic**: Via OpenAI compatibility layer, `claude-sonnet-4-20250514`
  - **LM Studio**: Fully local with auto-detection, no API key required
  
- **4-Tab Settings Modal** (`ui/src/components/chat/ApiKeyModal.tsx`)
  - Auto-fill base URLs per provider
  - Provider-specific placeholders and hints
  - Model dropdown with refresh capability
  
- **Provider-Aware Optimizations**:
  - Constrained providers get compressed prompts and reduced tool sets
  - HTTP timeout hierarchy: Groq 30s, Anthropic 60s, LMStudio/OpenAI 120s
  - Rate-limit detection with automatic wait-and-retry
  - Frontend SSE timeout: 360s > Backend agent: 300s > MCP session: 180s

#### Voice I/O - Speech Interaction
- **Speech-to-Text (STT)** (`ui/src/utils/vadRecorder.ts`)
  - Browser-based voice recording with Voice Activity Detection (VAD)
  - Web Audio AnalyserNode with RMS-based silence detection
  - Auto-stops after 1.8 seconds of silence
  - Real-time volume visualization on microphone button
  - Backend endpoints: `/api/voice/speech-to-text`
  - Groq: `whisper-large-v3-turbo` | OpenAI: `whisper-1`
  
- **Text-to-Speech (TTS)** (`ui/src/utils/streamingTTS.ts`)
  - Streaming TTS that reads AI responses as they arrive
  - Sentence-boundary detection for natural pacing (min 40 chars per chunk)
  - Gapless audio queue for smooth playback
  - Speaker button toggle (purple when active)
  - Backend endpoints: `/api/voice/text-to-speech`, `/api/voice/capabilities`
  - Groq: Orpheus TTS (200 char chunks, WAV) | OpenAI: tts-1 (4096 char chunks, MP3)

#### Fine-Tuning Pipeline
- **Dataset Generation** (`training/generate_dataset.py`)
  - 18 conversation generators for ComfyUI tool-calling tasks
  - Augmentation with parameter variations
  - 9 current + 8 future tool schemas
  - 11 workflow templates with parameter pools
  
- **Dataset Validation** (`training/validate_dataset.py`)
  - 5-pass validation: structural + semantic checks
  - JSON schema validation for tool calls
  - Turn sequence validation
  
- **QLoRA Training** (`training/train.py`)
  - Unsloth-based training framework
  - Qwen3 model support with GGUF export
  - Consumer GPU optimized (RTX 5060 8GB validated)
  - Chunked cross-entropy loss (128-token chunks, ~37 MB vs 1.18 GB full)
  - Windows WDDM-compatible gradient checkpointing
  - Python 3.14 compatibility patches

### Fixed

#### LM Studio Integration - Complete Overhaul
- **Port Configuration** (`backend/controller/llm_api.py`, `ui/src/components/chat/ApiKeyModal.tsx`)
  - FIXED: Port hint was wrong (1235 → 1234)
  - Correct default URL: `http://localhost:1234/v1`
  
- **URL Normalization** (`backend/utils/globals.py`)
  - FIXED: `/api/v1` was not being converted to `/v1` for OpenAI SDK compatibility
  - Automatic URL normalization: strips `/api` prefix, ensures `/v1` suffix
  - Handles both `http://localhost:1234` and `http://localhost:1234/v1` inputs
  
- **Model Listing** (`backend/controller/llm_api.py`)
  - FIXED: Did not parse LM Studio's native response format
  - Robust multi-format parser handles both OpenAI and LM Studio response formats
  - LM Studio format: `{"models": [...]}` with `key`/`display_name` fields
  - OpenAI format: `{"data": [...]}` with `id` field
  - 24-hour cache invalidation for model lists
  
- **API Key Handling** (`backend/service/mcp_client.py`, UI)
  - FIXED: API key was required even though LM Studio doesn't need one
  - Uses `"lmstudio-local"` placeholder when API key is empty
  - Frontend allows empty API key for LM Studio
  
- **Header Forwarding** (`backend/controller/conversation_api.py`)
  - FIXED: `Openai-Base-Url` header was not being sent from frontend
  - Proper header forwarding for custom base URLs
  
- **Auto-Detection** (`backend/utils/globals.py`)
  - Provider detection via URL patterns: `localhost:1234`, `127.0.0.1:1234`, `lmstudio`
  - Automatic feature flagging for local models

#### Metadata Handling
- **None-Safe Operations** (various files)
  - FIXED: Crashes when node metadata was None or malformed
  - Uses `(meta.get("field") or "").lower()` pattern
  - Guards: `if not isinstance(meta, dict): continue`

#### Canvas Rule Enforcement
- **Tool Restrictions** (`backend/service/mcp_client.py`, tool implementations)
  - FIXED: Tools could unintentionally modify canvas state
  - Only `save_workflow` modifies the canvas
  - `explain_node` and `search_node` are read-only information tools
  - Enforcement at code level (not just prompts) for local model compatibility

### Changed

#### Architecture
- **Provider Detection** (`backend/utils/globals.py`)
  - Added `detect_provider()` with URL pattern matching
  - Centralized provider constants: `GROQ_HTTP_TIMEOUT`, `ANTHROPIC_HTTP_TIMEOUT`, etc.
  
- **Agent Factory** (`backend/agent_factory.py`)
  - Provider-aware client configuration
  - Timeout propagation from provider detection
  
- **Settings Modal** (`ui/src/components/chat/ApiKeyModal.tsx`)
  - Restructured as 4-tab interface (was single form)
  - Auto-fill functionality for base URLs
  - Provider-specific help text and placeholders
  
- **Chat Input** (`ui/src/components/chat/ChatInput.tsx`)
  - Added agent mode toggle button (robot icon)
  - Added voice input button (microphone icon)
  - Visual indicators for active modes

#### API Endpoints
- **New Endpoints** (`backend/controller/conversation_api.py`, `backend/controller/llm_api.py`)
  - `POST /api/workflow/agent-mode-stream` - Agent mode SSE stream
  - `POST /api/voice/speech-to-text` - STT transcription
  - `POST /api/voice/text-to-speech` - TTS audio generation
  - `GET /api/voice/capabilities` - Provider TTS/STT capability check
  
- **Updated Endpoints**:
  - `GET /api/llm/models` - Now handles multiple provider formats
  - `POST /api/llm/verify` - Added base URL forwarding

#### Documentation
- **README.md** - Complete rewrite with feature comparison table
- **Added Files**:
  - `HOW_TO_USE_LMSTUDIO.md` - LM Studio setup guide
  - `LMSTUDIO_SETUP.md` - Detailed configuration steps
  - `LMSTUDIO_IMPLEMENTATION.md` - Technical implementation details
- **Authors.txt** - Updated attribution

### Dependencies

#### New Python Packages
- `unsloth` - QLoRA training framework (training pipeline only)
- Enhanced OpenAI SDK usage for multi-provider support

#### Updated Node Packages
- Enhanced React components for agent mode UI
- Added audio recording/playback utilities

### Technical Details

#### Timeout Hierarchy
```
Frontend SSE: 360s
  └─> Backend Agent: 300s
      └─> MCP Session: 180s
          └─> MCP Request: 120s
              └─> Provider HTTP: 30-120s (provider-dependent)
```

#### Tool Budget Enforcement
- Prevents runaway agent loops
- Per-tool limits configurable in `agent_mode_tools.py`
- Hard kill if tool abuse detected (3x same call in 8 turns)

#### Provider Detection Logic
```python
def detect_provider(base_url: str) -> str:
    url_lower = base_url.lower()
    if "groq" in url_lower: return "groq"
    if "anthropic" in url_lower: return "anthropic"
    if "localhost:1234" in url_lower or "lmstudio" in url_lower: return "lmstudio"
    return "openai"  # default
```

## [2.0.0] - Original Upstream Release

Features from the original [AIDC-AI/ComfyUI-Copilot](https://github.com/AIDC-AI/ComfyUI-Copilot) v2.0:

- Workflow generation with library matching
- One-click debug mode
- Workflow rewriting via natural language
- Parameter tuning (GenLab)
- Node search and recommendations
- Node query tool
- Model recommendations
- Downstream node suggestions
- Multilingual support (English, Chinese)

---

## Upgrade Guide

### From Upstream v2.0 to This Fork v3.0

1. **Install new dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Update API configuration**:
   - Open the settings modal in ComfyUI
   - Your existing OpenAI key will continue to work
   - If using LM Studio, clear the API key field and update the base URL to `http://localhost:1234/v1`

3. **Optional: Try new features**:
   - Enable Agent Mode with the robot button
   - Enable Voice I/O with the speaker button
   - Test multiple providers by switching tabs in settings

### Breaking Changes

- **LM Studio URL format**: Old format `http://localhost:1235/api/v1` → New format `http://localhost:1234/v1`
  - The system will auto-normalize, but update your saved configuration for clarity

### Migration Notes

- All existing workflows are compatible
- Chat history is preserved
- Settings may need to be re-entered if base URL format changed

---

## Support and Feedback

For issues or questions:
- **This fork**: https://github.com/vehoelite/ComfyUI-Copilot-w-Agent/issues
- **Original project**: https://github.com/AIDC-AI/ComfyUI-Copilot/issues

## Credits

- **Original ComfyUI-Copilot v2.0**: [AIDC-AI](https://github.com/AIDC-AI)
- **Fork enhancements v3.0**: Enhanced by Claude Opus 4.6
- **ComfyUI**: [ComfyUI Project](https://github.com/comfyanonymous/ComfyUI)
- **Unsloth**: [Unsloth Project](https://github.com/unslothai/unsloth)
