'''
Author: ai-business-hql qingli.hql@alibaba-inc.com
Date: 2025-07-14 16:46:20
LastEditors: ai-business-hql ai.bussiness.hql@gmail.com
LastEditTime: 2025-12-15 15:03:28
FilePath: /comfyui_copilot/backend/controller/llm_api.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
# Copyright (C) 2025 AIDC-AI
# Licensed under the MIT License.

import json
from typing import List, Dict, Any
from aiohttp import web
from ..utils.globals import LLM_DEFAULT_BASE_URL, LMSTUDIO_DEFAULT_BASE_URL, OPENAI_API_KEY, OPENAI_BASE_URL, TENANT_ID, is_lmstudio_url, detect_provider
import server
import requests
from ..utils.logger import log
import aiohttp


# ---------------------------------------------------------------------------
# Model classification for color-coded model list
# ---------------------------------------------------------------------------

# Models that should be completely hidden from the chat model dropdown
_HIDDEN_MODELS = {
    # Guard / safety models
    "meta-llama/llama-guard-4-12b",
    "meta-llama/llama-prompt-guard-2-22m",
    "meta-llama/llama-prompt-guard-2-86m",
    "openai/gpt-oss-safeguard-20b",
    # TTS models
    "canopylabs/orpheus-v1-english",
    "canopylabs/orpheus-arabic-saudi",
    # STT models
    "whisper-large-v3",
    "whisper-large-v3-turbo",
    # Compound / orchestration
    "groq/compound",
    "groq/compound-mini",
}

# Green = excellent for tool calling & chat
_GREEN_MODELS = {
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
}

# Yellow = decent for chat, usable for tool calling
_YELLOW_MODELS = {
    "qwen/qwen3-32b",
    "moonshotai/kimi-k2-instruct",
    "moonshotai/kimi-k2-instruct-0905",
    "openai/gpt-oss-20b",
}

# Everything else that isn't hidden gets red (works but not ideal)
# e.g. llama-4 MoE models, small 7-8B models


def _classify_model(model_id: str) -> dict:
    """Classify a model and return its tier + visibility.
    
    Returns dict with:
      - hidden: bool  (filter out entirely)
      - tier: "green" | "yellow" | "red"
      - tier_label: human-readable tag
    """
    mid = model_id.lower().strip()
    
    # Check hidden
    for h in _HIDDEN_MODELS:
        if h.lower() == mid or mid.endswith(h.lower()):
            return {"hidden": True, "tier": "hidden", "tier_label": ""}
    
    # Check green
    for g in _GREEN_MODELS:
        if g.lower() in mid:
            return {"hidden": False, "tier": "green", "tier_label": "★ Recommended"}
    
    # Check yellow
    for y in _YELLOW_MODELS:
        if y.lower() in mid:
            return {"hidden": False, "tier": "yellow", "tier_label": "Good"}
    
    # Default: red
    return {"hidden": False, "tier": "red", "tier_label": "Basic"}


@server.PromptServer.instance.routes.get("/api/model_config")
async def list_models(request):
    """
    List available LLM models
    
    Returns:
        JSON response with models list in the format expected by frontend:
        {
            "models": [
                {"name": "model_name", "image_enable": boolean},
                ...
            ]
        }
    """
    try:
        log.info("Received list_models request")
        if TENANT_ID:
            model_list = [ "gemini-2.5-flash", "gpt-5-nano", "gpt-5-mini", "gpt-5" ]
            llm_config = []
            for model in model_list:
                llm_config.append({
                    "label": model,
                    "name": model,
                    "image_enable": True
                })
            return web.json_response({
                "models": llm_config
            })
        
        openai_api_key = request.headers.get('Openai-Api-Key') or OPENAI_API_KEY or ""
        openai_base_url = request.headers.get('Openai-Base-Url') or OPENAI_BASE_URL or LLM_DEFAULT_BASE_URL

        # Check if this is LMStudio and adjust URL accordingly
        provider = detect_provider(openai_base_url)
        is_lmstudio = provider == "lmstudio"
        
        # Normalize /api/v1 → /v1 for LMStudio so we hit the OpenAI-compatible
        # endpoint (/v1/models returns standard {data:[{id:...}]} format, while
        # /api/v1/models returns native format with key/display_name fields).
        models_base_url = openai_base_url
        if is_lmstudio and '/api/v1' in openai_base_url:
            models_base_url = openai_base_url.replace('/api/v1', '/v1')
            log.info(f"Normalized LMStudio URL for model listing: {openai_base_url} → {models_base_url}")

        request_url = f"{models_base_url}/models"
        
        headers = {}
        if not is_lmstudio or (is_lmstudio and openai_api_key):
            # Include Authorization header for OpenAI API, Groq, Anthropic, or LMStudio with API key
            headers["Authorization"] = f"Bearer {openai_api_key}"
        
        # Anthropic uses x-api-key header instead of Bearer token for native endpoint
        if provider == "anthropic":
            headers["x-api-key"] = openai_api_key
            headers["anthropic-version"] = "2023-06-01"
        
        log.info(f"Fetching models from: {request_url} (provider={provider})")
        response = requests.get(request_url, headers=headers, timeout=10)
        llm_config = []
        if response.status_code == 200:
            raw = response.json()
            log.info(f"Models response keys: {list(raw.keys()) if isinstance(raw, dict) else type(raw).__name__}")

            # Extract model list from various response formats
            model_list = []
            if isinstance(raw, dict):
                # Standard OpenAI format: {"data": [{"id": "..."}, ...]}
                if 'data' in raw and isinstance(raw['data'], list):
                    model_list = raw['data']
                # Alternate format: {"models": [...]}
                elif 'models' in raw and isinstance(raw['models'], list):
                    model_list = raw['models']
            elif isinstance(raw, list):
                model_list = raw

            for model in model_list:
                model_id = None
                if isinstance(model, str):
                    model_id = model
                elif isinstance(model, dict):
                    # Standard OpenAI: 'id', alternate: 'name'/'model',
                    # LMStudio native /api/v1: 'key'/'display_name'
                    model_id = model.get('id') or model.get('name') or model.get('model') or model.get('key') or model.get('display_name')
                if model_id:
                    classification = _classify_model(model_id)
                    if classification["hidden"]:
                        continue  # Skip guard, TTS, STT, compound models
                    llm_config.append({
                        "label": model_id,
                        "name": model_id,
                        "image_enable": True,
                        "tier": classification["tier"],
                        "tier_label": classification["tier_label"],
                    })
            
            # Sort: green first, then yellow, then red
            tier_order = {"green": 0, "yellow": 1, "red": 2}
            llm_config.sort(key=lambda m: (tier_order.get(m.get("tier", "red"), 2), m["label"].lower()))
            
            log.info(f"Parsed {len(llm_config)} models from LLM endpoint (hidden: {len(model_list) - len(llm_config)})")
        else:
            log.warning(f"Models endpoint returned status {response.status_code}: {response.text[:200]}")
        
        return web.json_response({
                "models": llm_config
            }
        )
        
    except Exception as e:
        log.error(f"Error in list_models: {str(e)}")
        return web.json_response({
            "error": f"Failed to list models: {str(e)}"
        }, status=500)


@server.PromptServer.instance.routes.get("/verify_openai_key")
async def verify_openai_key(req):
    """
    Verify if an OpenAI API key is valid by calling the OpenAI models endpoint
    Also supports LMStudio verification (which may not require an API key)
    
    Returns:
        JSON response with success status and message
    """
    try:
        openai_api_key = req.headers.get('Openai-Api-Key')
        openai_base_url = req.headers.get('Openai-Base-Url', 'https://api.openai.com/v1')
        
        # Check if this is LMStudio
        provider = detect_provider(openai_base_url)
        is_lmstudio = provider == "lmstudio"
        
        # For LMStudio, API key might not be required
        # For Groq/Anthropic, API key IS required
        if not openai_api_key and not is_lmstudio:
            return web.json_response({
                "success": False, 
                "message": "No API key provided"
            })
        
        # Use a direct HTTP request instead of the OpenAI client
        # This gives us more control over the request method and error handling
        headers = {}
        if not is_lmstudio or (is_lmstudio and openai_api_key):
            # Include Authorization header for OpenAI API, Groq, or LMStudio with API key
            headers["Authorization"] = f"Bearer {openai_api_key}"
        
        # Anthropic uses x-api-key header
        if provider == "anthropic":
            headers["x-api-key"] = openai_api_key
            headers["anthropic-version"] = "2023-06-01"
        
        # Make a simple GET request to the models endpoint
        # Normalize /api/v1 → /v1 for LMStudio to use OpenAI-compatible endpoint
        verify_base_url = openai_base_url
        if is_lmstudio and '/api/v1' in openai_base_url:
            verify_base_url = openai_base_url.replace('/api/v1', '/v1')
        response = requests.get(f"{verify_base_url}/models", headers=headers, timeout=10)
        
        # Check if the request was successful
        if response.status_code == 200:
            provider_name = {"groq": "Groq", "anthropic": "Anthropic", "lmstudio": "LMStudio"}.get(provider, "API")
            success_message = f"{provider_name} connection successful" if provider != "openai" else "API key is valid"
            return web.json_response({
                "success": True, 
                "data": True, 
                "message": success_message
            })
        else:
            log.error(f"API validation failed with status code: {response.status_code}")
            provider_name = {"groq": "Groq", "anthropic": "Anthropic", "lmstudio": "LMStudio"}.get(provider, "API")
            error_message = f"{provider_name} connection failed: HTTP {response.status_code} - {response.text[:200]}"
            return web.json_response({
                "success": False, 
                "data": False,
                "message": error_message
            })
            
    except Exception as e:
        log.error(f"Error verifying API key/connection: {str(e)}")
        error_message = f"Invalid API key: {str(e)}"
        if 'base_url' in locals() and is_lmstudio_url(locals().get('openai_base_url', '')):
            error_message = f"LMStudio connection error: {str(e)}"
        return web.json_response({
            "success": False, 
            "data": False, 
            "message": error_message
        })


# ---------------------------------------------------------------------------
# Voice provider auto-detection & defaults
# ---------------------------------------------------------------------------

# Maps provider → { tts_model, tts_voices, stt_model, supported }
_VOICE_PROVIDER_MAP = {
    "groq": {
        "supported": True,
        "tts_model": "canopylabs/orpheus-v1-english",
        "tts_voices": ["troy", "autumn", "diana", "hannah", "austin", "Daniel"],
        "stt_model": "whisper-large-v3-turbo",
        "tts_format": "wav",
        "max_chunk": 200,
    },
    "openai": {
        "supported": True,
        "tts_model": "tts-1",
        "tts_voices": ["alloy", "echo", "fable", "nova", "onyx", "shimmer"],
        "stt_model": "whisper-1",
        "tts_format": "mp3",
        "max_chunk": 4096,
    },
    "anthropic": {"supported": False},
    "lmstudio":  {"supported": False},
}


def _resolve_voice_provider(request) -> dict:
    """Resolve voice provider config from explicit override headers or auto-detect from chat base URL.
    
    Override headers (take priority):
      Voice-Provider: groq | openai | ...
      Voice-Api-Key:  <key for the voice provider>
      Voice-Base-Url: <base url for the voice provider>
    
    Auto-detect fallback: uses the chat Openai-Base-Url header to detect provider.
    """
    # --- Explicit override ---
    voice_provider = (request.headers.get('Voice-Provider') or '').strip().lower()
    voice_api_key  = request.headers.get('Voice-Api-Key', '').strip()
    voice_base_url = request.headers.get('Voice-Base-Url', '').strip()
    
    if voice_provider and voice_provider in _VOICE_PROVIDER_MAP:
        cfg = _VOICE_PROVIDER_MAP[voice_provider]
        if not cfg.get("supported"):
            return {"error": f"Provider '{voice_provider}' does not support voice features"}
        api_key  = voice_api_key or request.headers.get('Openai-Api-Key') or OPENAI_API_KEY or ""
        base_url = voice_base_url or {
            "groq":   "https://api.groq.com/openai/v1",
            "openai": "https://api.openai.com/v1",
        }.get(voice_provider, "")
        return {**cfg, "api_key": api_key, "base_url": base_url}
    
    # --- Auto-detect from chat base URL ---
    chat_base_url = request.headers.get('Openai-Base-Url') or OPENAI_BASE_URL or LLM_DEFAULT_BASE_URL
    provider = detect_provider(chat_base_url)
    cfg = _VOICE_PROVIDER_MAP.get(provider, _VOICE_PROVIDER_MAP["openai"])
    
    if not cfg.get("supported"):
        return {"error": f"Your current provider ({provider}) does not support voice. Configure a voice provider (Groq or OpenAI) in Settings → Voice."}
    
    api_key  = voice_api_key or request.headers.get('Openai-Api-Key') or OPENAI_API_KEY or ""
    base_url = voice_base_url or chat_base_url
    
    return {**cfg, "api_key": api_key, "base_url": base_url}


# ---------------------------------------------------------------------------
# Voice capability check
# ---------------------------------------------------------------------------

@server.PromptServer.instance.routes.get("/api/voice/capabilities")
async def voice_capabilities(request):
    """Return whether voice features are available for the current configuration."""
    cfg = _resolve_voice_provider(request)
    if "error" in cfg:
        return web.json_response({
            "tts": False, "stt": False,
            "error": cfg["error"],
        })
    return web.json_response({
        "tts": True, "stt": True,
        "tts_voices": cfg.get("tts_voices", []),
        "default_voice": cfg.get("tts_voices", ["alloy"])[0],
        "provider": detect_provider(cfg.get("base_url", "")),
    })


# ---------------------------------------------------------------------------
# Voice: Text-to-Speech
# ---------------------------------------------------------------------------

@server.PromptServer.instance.routes.post("/api/voice/tts")
async def voice_tts(request):
    """Convert text to speech using auto-detected or manually configured voice provider.
    
    Expects JSON body: { "text": "...", "voice": "troy" }
    Optional headers: Voice-Provider, Voice-Api-Key, Voice-Base-Url
    Returns: audio bytes.
    """
    try:
        cfg = _resolve_voice_provider(request)
        if "error" in cfg:
            return web.json_response({"error": cfg["error"]}, status=400)
        
        body = await request.json()
        text = body.get("text", "").strip()
        if not text:
            return web.json_response({"error": "No text provided"}, status=400)
        
        voice = body.get("voice") or cfg["tts_voices"][0]
        model = body.get("model") or cfg["tts_model"]
        response_format = cfg.get("tts_format", "wav")
        max_chunk = cfg.get("max_chunk", 200)
        
        tts_url = f"{cfg['base_url']}/audio/speech"
        headers = {
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
        }
        
        # Split long text into chunks
        chunks = []
        remaining = text
        while len(remaining) > max_chunk:
            idx = remaining.rfind('. ', 0, max_chunk)
            if idx < 0:
                idx = remaining.rfind(' ', 0, max_chunk)
            if idx < 0:
                idx = max_chunk
            else:
                idx += 1
            chunks.append(remaining[:idx].strip())
            remaining = remaining[idx:].strip()
        if remaining:
            chunks.append(remaining)
        
        audio_parts = []
        async with aiohttp.ClientSession() as session:
            for chunk in chunks:
                payload = {
                    "model": model,
                    "input": chunk,
                    "voice": voice,
                    "response_format": response_format,
                }
                async with session.post(tts_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        log.error(f"TTS API error {resp.status}: {error_text[:300]}")
                        # Pass through meaningful provider errors (e.g., Groq terms acceptance)
                        try:
                            err_json = json.loads(error_text)
                            err_msg = err_json.get("error", {}).get("message", "") if isinstance(err_json.get("error"), dict) else str(err_json.get("error", ""))
                            err_code = err_json.get("error", {}).get("code", "") if isinstance(err_json.get("error"), dict) else ""
                        except Exception:
                            err_msg = error_text[:200]
                            err_code = ""
                        return web.json_response({
                            "error": err_msg or f"TTS API error: {resp.status}",
                            "code": err_code,
                        }, status=resp.status)
                    audio_parts.append(await resp.read())
        
        audio_data = b"".join(audio_parts)
        content_type = "audio/mpeg" if response_format == "mp3" else f"audio/{response_format}"
        
        return web.Response(
            body=audio_data,
            content_type=content_type,
            headers={"Content-Disposition": "inline"},
        )
        
    except Exception as e:
        log.error(f"TTS error: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ---------------------------------------------------------------------------
# Voice: Speech-to-Text
# ---------------------------------------------------------------------------

@server.PromptServer.instance.routes.post("/api/voice/stt")
async def voice_stt(request):
    """Transcribe audio to text using auto-detected or manually configured voice provider.
    
    Expects multipart form data with an 'audio' file field.
    Optional headers: Voice-Provider, Voice-Api-Key, Voice-Base-Url
    Returns: { "text": "transcribed text" }
    """
    try:
        cfg = _resolve_voice_provider(request)
        if "error" in cfg:
            return web.json_response({"error": cfg["error"]}, status=400)
        
        reader = await request.multipart()
        audio_data = None
        stt_model = cfg["stt_model"]
        
        async for field in reader:
            if field.name == "audio":
                audio_data = await field.read()
            elif field.name == "model":
                stt_model = (await field.read()).decode() or stt_model
        
        if not audio_data:
            return web.json_response({"error": "No audio file provided"}, status=400)
        
        stt_url = f"{cfg['base_url']}/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {cfg['api_key']}",
        }
        
        form = aiohttp.FormData()
        form.add_field("file", audio_data, filename="audio.webm", content_type="audio/webm")
        form.add_field("model", stt_model)
        form.add_field("response_format", "json")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(stt_url, data=form, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    log.error(f"STT API error {resp.status}: {error_text[:300]}")
                    return web.json_response({"error": f"STT API error: {resp.status}"}, status=resp.status)
                result = await resp.json()
        
        transcribed_text = result.get("text", "")
        log.info(f"STT transcribed {len(transcribed_text)} chars")
        
        return web.json_response({"text": transcribed_text})
        
    except Exception as e:
        log.error(f"STT error: {e}")
        return web.json_response({"error": str(e)}, status=500)