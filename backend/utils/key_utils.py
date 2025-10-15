'''
Author: ai-business-hql ai.bussiness.hql@gmail.com
Date: 2025-10-11 16:46:10
LastEditors: ai-business-hql ai.bussiness.hql@gmail.com
LastEditTime: 2025-10-15 14:35:41
FilePath: /ComfyUI-Copilot/backend/utils/key_utils.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from copy import deepcopy

def workflow_config_adapt(config: dict) -> dict:
    """Return a deep-copied and adapted workflow config without mutating input.

    - Map workflow_llm_api_key -> openai_api_key (and null out original key)
    - Map workflow_llm_base_url -> openai_base_url (and null out original key)
    """
    if not config:
        return {}

    new_config = deepcopy(config)

    if new_config.get("workflow_llm_api_key"):
        new_config["openai_api_key"] = new_config.get("workflow_llm_api_key")
        new_config["workflow_llm_api_key"] = None
    if new_config.get("workflow_llm_base_url"):
        new_config["openai_base_url"] = new_config.get("workflow_llm_base_url")
        new_config["workflow_llm_base_url"] = None
    if new_config.get("workflow_llm_model"):
        new_config["model_select"] = new_config.get("workflow_llm_model")
        new_config["workflow_llm_model"] = None
    else:
        new_config["model_select"] = None

    return new_config
