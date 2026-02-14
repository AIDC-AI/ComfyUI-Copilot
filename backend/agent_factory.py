'''
Author: ai-business-hql qingli.hql@alibaba-inc.com
Date: 2025-07-31 19:38:08
LastEditors: ai-business-hql ai.bussiness.hql@gmail.com
LastEditTime: 2026-01-12 11:11:53
FilePath: /comfyui_copilot/backend/agent_factory.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''

try:
    from agents import Agent, OpenAIChatCompletionsModel, ModelSettings, Runner, set_tracing_disabled, set_default_openai_api
    if not hasattr(__import__('agents'), 'Agent'):
        raise ImportError
except Exception:
    # Give actionable guidance without crashing obscurely
    raise ImportError(
        "Detected incorrect or missing 'agents' package. "
        "Please uninstall legacy RL 'agents' (and tensorflow/gym if pulled transitively) and install openai-agents. "
        "Commands:\n"
        "  python -m pip uninstall -y agents gym tensorflow\n"
        "  python -m pip install -U openai-agents\n\n"
        "Alternatively, keep both by setting COMFYUI_COPILOT_PREFER_OPENAI_AGENTS=1 so this plugin prefers openai-agents."
    )
from dotenv import dotenv_values
from .utils.globals import (
    LLM_DEFAULT_BASE_URL, LMSTUDIO_DEFAULT_BASE_URL,
    GROQ_DEFAULT_BASE_URL, ANTHROPIC_DEFAULT_BASE_URL,
    get_comfyui_copilot_api_key, is_lmstudio_url, detect_provider,
)
from openai import AsyncOpenAI
import httpx


from agents._config import set_default_openai_api
from agents.tracing import set_tracing_disabled
import asyncio
# from .utils.logger import log

# def load_env_config():
#     """Load environment variables from .env.llm file"""
#     from dotenv import load_dotenv

#     env_file_path = os.path.join(os.path.dirname(__file__), '.env.llm')
#     if os.path.exists(env_file_path):
#         load_dotenv(env_file_path)
#         log.info(f"Loaded environment variables from {env_file_path}")
#     else:
#         log.warning(f"Warning: .env.llm not found at {env_file_path}")


# # Load environment configuration
# load_env_config()

set_default_openai_api("chat_completions")
set_tracing_disabled(False)


def create_agent(**kwargs) -> Agent:
    # 通过用户配置拿/环境变量
    config = kwargs.pop("config") if "config" in kwargs else {}
    # 避免将 None 写入 headers
    session_id = (config or {}).get("session_id")
    default_headers = {}
    if session_id:
        default_headers["X-Session-ID"] = session_id

    # Determine base URL and API key
    base_url = LLM_DEFAULT_BASE_URL
    api_key = get_comfyui_copilot_api_key() or ""

    if config:
        if config.get("openai_base_url") and config.get("openai_base_url") != "":
            base_url = config.get("openai_base_url")
        if config.get("openai_api_key") and config.get("openai_api_key") != "":
            api_key = config.get("openai_api_key")

    # Detect provider from URL
    provider = detect_provider(base_url)

    # Check if this is LMStudio and adjust API key handling
    is_lmstudio = provider == "lmstudio"
    if is_lmstudio and not api_key:
        # LMStudio typically doesn't require an API key, use a placeholder
        api_key = "lmstudio-local"

    # Groq: ensure API key exists
    if provider == "groq" and not api_key:
        api_key = config.get("openai_api_key") or ""

    # Anthropic: ensure API key exists
    if provider == "anthropic" and not api_key:
        api_key = config.get("openai_api_key") or ""

    # The OpenAI SDK appends /chat/completions to the base_url.
    # LMStudio's native API uses /api/v1/chat (not /api/v1/chat/completions),
    # so we normalize /api/v1 to /v1 which hits the OpenAI-compatible endpoint.
    sdk_base_url = base_url
    if is_lmstudio and '/api/v1' in base_url:
        sdk_base_url = base_url.replace('/api/v1', '/v1')

    # Provider-specific timeout tuning:
    # - Groq is blazing fast (cloud inference on LPU), 30s is generous
    # - Anthropic cloud: 60s is usually plenty
    # - LMStudio local: 120s because CPU offloading is slow
    # - OpenAI/default: 120s
    timeout_map = {
        "groq": httpx.Timeout(30.0, connect=10.0),
        "anthropic": httpx.Timeout(60.0, connect=10.0),
        "lmstudio": httpx.Timeout(120.0, connect=15.0),
        "openai": httpx.Timeout(120.0, connect=15.0),
    }
    _timeout = timeout_map.get(provider, timeout_map["openai"])

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=sdk_base_url,
        default_headers=default_headers,
        timeout=_timeout,
        max_retries=1,
    )

    # Determine model with proper precedence:
    # 1) Explicit selection from config (model_select or model from frontend)
    # 2) Explicit kwarg 'model' (call-site override)
    model_from_config = (config or {}).get("model_select") or (config or {}).get("model")
    model_from_kwargs = kwargs.pop("model", None)

    model_name = model_from_config or model_from_kwargs or "gemini-2.5-flash"

    # Default model per provider when no model is explicitly selected
    if model_name == "gemini-2.5-flash":
        provider_default_models = {
            "groq": "llama-3.3-70b-versatile",
            "anthropic": "claude-sonnet-4-20250514",
            "lmstudio": model_name,  # user must select from loaded models
            "openai": "gpt-4.1-mini",
        }
        model_name = provider_default_models.get(provider, model_name)

    model = OpenAIChatCompletionsModel(model_name, openai_client=client)

    # Safety: ensure no stray 'model' remains in kwargs to avoid duplicate kwarg errors
    kwargs.pop("model", None)

    if config.get("max_tokens"):
        return Agent(model=model, model_settings=ModelSettings(max_tokens=config.get("max_tokens") or 8192), **kwargs)
    return Agent(model=model, **kwargs)