[中文](./README_CN.md) | English

<div align="center">

# ComfyUI-Copilot-w-Agent

### Your Intelligent ComfyUI Assistant - Now with Agent Mode, Voice, and Multi-Provider Support

**A community-enhanced fork of [AIDC-AI/ComfyUI-Copilot](https://github.com/AIDC-AI/ComfyUI-Copilot)**

<h4>

<img src="https://img.shields.io/badge/Version-3.0.0-blue.svg" alt="Version">
<img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
<img src="https://img.shields.io/badge/python-3.10%2B-purple.svg" alt="Python">
<img src="https://img.shields.io/badge/Enhanced_by-Claude_Opus_4.6-orange.svg" alt="Claude Opus 4.6">

</h4>

</div>

---

## What's Different in This Fork?

This fork builds on the excellent [ComfyUI-Copilot v2.0](https://github.com/AIDC-AI/ComfyUI-Copilot) by AIDC-AI, adding significant new capabilities:

| Feature | Upstream v2.0 | This Fork v3.0 |
|---------|:---:|:---:|
| **Agent Mode** (autonomous multi-step workflows) | - | Yes |
| **Multi-Provider** (OpenAI, Groq, Anthropic, LMStudio) | OpenAI only | Yes |
| **LM Studio Integration** (fixed and working) | Broken | Yes |
| **Voice I/O** (STT + streaming TTS) | - | Yes |
| **Provider-Aware Timeouts and Token Budgets** | - | Yes |
| **Loop Prevention and Tool Budget Enforcement** | - | Yes |
| **Fine-Tuning Pipeline** (Qwen3 QLoRA for tool-calling) | - | Yes |
| Chat, Debug, Rewrite, GenLab | Yes | Yes |

---

## New Features

### Agent Mode - Autonomous Workflow Building

Agent Mode lets the AI autonomously plan and execute multi-step tasks on your ComfyUI canvas. Instead of asking for one thing at a time, describe your goal and the agent will:

1. **Plan** - Break the goal into discrete tasks
2. **Execute** - Search nodes, build workflows, set parameters
3. **Validate** - Check the workflow for errors
4. **Report** - Summarize what was done and ask for confirmation

Toggle Agent Mode with the robot button in the chat input. A visual step tracker shows real-time progress.

**Architecture:**
- `backend/service/agent_mode.py` - PLAN, EXECUTE, VALIDATE, REPORT loop
- `backend/service/agent_mode_tools.py` - Task queue, tool call tracker, loop prevention
- `ui/src/components/chat/AgentModeIndicator.tsx` - Visual progress indicator

**Safety:**
- Per-tool call limits (e.g., `search_nodes` max 4x, `save_workflow` max 5x)
- Global tool budget of 30 calls per session
- Hard kill if same tool+args repeated 3x in last 8 calls
- 5-minute total timeout, 25 max agent turns

---

### Multi-Provider Support

Use any OpenAI-compatible provider - no lock-in.

| Provider | Base URL | Default Model | Notes |
|----------|----------|---------------|-------|
| **OpenAI** | `https://api.openai.com/v1` | `gemini-2.5-flash` | Full feature support |
| **Groq** | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` | Free tier, blazing fast |
| **Anthropic** | `https://api.anthropic.com/v1` | `claude-sonnet-4-20250514` | Via OpenAI compatibility |
| **LM Studio** | `http://localhost:1234/v1` | Auto-detected | Fully local, no API key |

The settings modal has **4 tabs** with auto-fill base URLs and provider-specific placeholders. Provider is auto-detected from the base URL.

**Provider-aware optimizations:**
- Constrained providers (Groq free tier, LMStudio) get reduced tool sets and compressed prompts
- Provider-specific HTTP timeouts (Groq 30s, Anthropic 60s, LMStudio/OpenAI 120s)
- Rate-limit detection with automatic wait-and-retry

---

### LM Studio Integration - Fixed

The upstream LM Studio integration had several issues that made it non-functional:

**What was broken:**
- Port hint was wrong (1235 instead of 1234)
- URL normalization failed - `/api/v1` was not being converted to `/v1` for the OpenAI SDK
- Model listing did not parse LM Studio's native response format (`{"models": [...]}` with `key`/`display_name` fields)
- API key was required even though LM Studio does not need one
- The `Openai-Base-Url` header was not being sent from the frontend
- No cache invalidation for model lists (stale after 24h)

**What was fixed:**
- Correct default URL: `http://localhost:1234/v1`
- Automatic URL normalization (strips `/api` prefix, ensures `/v1` suffix)
- Robust multi-format model list parser (handles both OpenAI and LM Studio response formats)
- API key is optional - uses `"lmstudio-local"` placeholder when empty
- Proper header forwarding for base URL
- 24-hour cache invalidation for model lists
- Auto-detection of LM Studio via URL patterns

See [HOW_TO_USE_LMSTUDIO.md](HOW_TO_USE_LMSTUDIO.md) for setup instructions.

---

### Voice I/O - Talk to Your Copilot

Full voice input/output with per-provider backend support:

**Speech-to-Text (STT):**
- Browser-based voice recording with Voice Activity Detection (VAD)
- Auto-stops after 1.8 seconds of silence
- Real-time volume visualization on the mic button
- Groq: `whisper-large-v3-turbo` | OpenAI: `whisper-1`

**Text-to-Speech (TTS):**
- Streaming TTS that reads responses as they arrive
- Sentence-boundary detection for natural pacing (min 40 chars per chunk)
- Gapless audio queue for smooth playback
- Groq: Orpheus TTS (200 char chunks, WAV) | OpenAI: tts-1 (4096 char chunks, MP3)
- Toggle with the speaker button (purple when active)

**Key files:**
- `ui/src/utils/streamingTTS.ts` - Sentence extraction, audio queue, gapless playback
- `ui/src/utils/vadRecorder.ts` - Web Audio AnalyserNode, RMS-based silence detection
- `backend/controller/llm_api.py` - `_VOICE_PROVIDER_MAP`, TTS/STT endpoints, `GET /api/voice/capabilities`

---

### Fine-Tuning Pipeline

A complete training pipeline for fine-tuning Qwen3 models on ComfyUI tool-calling tasks:

`
training/
  generate_dataset.py    # 18 conversation generators, augmentation
  validate_dataset.py    # 5-pass structural + semantic validation
  train.py               # QLoRA training with Unsloth + GGUF export
  tool_schemas.py        # 9 current + 8 future tool definitions
  workflow_templates.py  # 11 workflow templates + parameter pools
`

**Designed for consumer GPUs:**
- Chunked cross-entropy loss (128-token chunks, ~37 MB vs 1.18 GB full)
- Windows WDDM-compatible gradient checkpointing (no CPU offloading)
- Python 3.14 compatibility patches
- RTX 5060 8GB validated (Qwen3-4B, 4-bit, 2048 seq len)

---

## Inherited Features (from Upstream v2.0)

All original ComfyUI-Copilot features work as before:

- **Workflow Generation** - Describe what you want, get 3 library matches + 1 AI-generated workflow
- **One-Click Debug** - Auto-detect errors, fix parameters, repair connections
- **Workflow Rewriting** - Modify existing workflows via natural language
- **Parameter Tuning (GenLab)** - Batch parameter sweeps with visual comparison
- **Node Recommendations** - Search and discover nodes by description
- **Node Query** - Deep-dive into any node's inputs, outputs, and usage
- **Model Recommendations** - Find checkpoints and LoRAs for your use case
- **Downstream Node Suggestions** - Context-aware next-node recommendations

---

## Getting Started

### Installation

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/vehoelite/ComfyUI-Copilot-w-Agent.git
cd ComfyUI-Copilot-w-Agent
pip install -r requirements.txt
```

Windows (embedded Python):
```bash
python_embeded\python.exe -m pip install -r ComfyUI\custom_nodes\ComfyUI-Copilot-w-Agent\requirements.txt
```

### Configuration

1. **Launch ComfyUI** and find the Copilot button on the left panel
2. **Click the settings button** to open the API configuration modal
3. **Choose your provider** tab (OpenAI, Groq, Anthropic, or LM Studio)
4. **Enter your API key** (or leave empty for LM Studio)
5. **Verify the connection** and select a model

### Using Agent Mode

1. Toggle the robot button in the chat input
2. Describe your goal: *"Build a workflow that generates an image, upscales it 4x, and fixes faces"*
3. Watch the agent plan and execute steps automatically
4. Review the result and confirm or iterate

### Using Voice

1. Enable voice with the speaker button
2. Click the microphone to speak your request
3. AI responses will be read aloud as they stream in

---

## Architecture

`
Backend (Python)
  OpenAI Agents SDK + aiohttp via ComfyUI's PromptServer
  agent_factory.py        - Creates Agent with AsyncOpenAI client
  service/
    agent_mode.py          - Agent Mode orchestration (PLAN, EXECUTE, VALIDATE, REPORT)
    agent_mode_tools.py    - Tool budget, loop prevention, task queue
    mcp_client.py          - Main chat agent entry point
    debug_agent.py         - Multi-agent workflow debugger
    workflow_rewrite_agent.py - Workflow modification
  controller/
    conversation_api.py    - SSE streaming endpoints
    llm_api.py             - Model listing, verification, TTS/STT, voice capabilities
  utils/
    globals.py             - detect_provider(), provider constants
    comfy_gateway.py       - Wraps ComfyUI HTTP APIs

Frontend (React + Vite + Tailwind)
  workflowChat/workflowChat.tsx - Main chat + agent mode handling
  components/chat/
    ChatInput.tsx           - Agent mode toggle, voice buttons
    AgentModeIndicator.tsx  - Visual step tracker
    ApiKeyModal.tsx         - 4-tab provider configuration
  apis/workflowChatApi.ts   - API layer (streamAgentMode, textToSpeech, etc.)
  utils/
    streamingTTS.ts         - Streaming text-to-speech with sentence extraction
    vadRecorder.ts          - Voice activity detection recorder
`

---

## Technical Decisions

**Timeout Hierarchy:** Frontend SSE (360s) > Backend Agent (300s) > MCP session (180s) > MCP request (120s) > Provider HTTP (30-120s)

**Canvas Rule:** Only `save_workflow` modifies the canvas. `explain_node` and `search_node` are read-only information tools.

**Tool Enforcement:** Local models ignore prompt-level rules. Enforcement is at code level via tools that refuse to execute, plus stream-level kill switches.

**None-safe metadata:** Uses `(meta.get("field") or "").lower()` with `if not isinstance(meta, dict): continue` guard.

---

## Contributing

Contributions welcome! This fork aims to push ComfyUI-Copilot's capabilities forward while staying compatible with upstream.

### Contributing to This Fork
- **Bug reports** - Open an issue with reproduction steps
- **Feature requests** - Describe the use case
- **Pull requests** - Fork, branch, PR with clear description

### Contributing Back to Original Repository
Want to help contribute these enhancements to the original ComfyUI-Copilot project? See:
- **[HOW_TO_SUBMIT_PR.md](./HOW_TO_SUBMIT_PR.md)** - Detailed guide for submitting PRs to upstream
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - General contribution guidelines
- **[NEXT_STEPS.md](./NEXT_STEPS.md)** - Quick start guide for getting your changes merged

We've prepared comprehensive documentation to make it easy to contribute these fixes and features back to AIDC-AI's original repository.

---

## Credits

- **[AIDC-AI](https://github.com/AIDC-AI)** - Original ComfyUI-Copilot (v2.0)
- **Claude Opus 4.6** - Agent Mode, multi-provider support, voice I/O, LM Studio fixes, fine-tuning pipeline, and all enhancements in this fork
- **[Unsloth](https://github.com/unslothai/unsloth)** - QLoRA training framework

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Original project: [AIDC-AI/ComfyUI-Copilot](https://github.com/AIDC-AI/ComfyUI-Copilot)
