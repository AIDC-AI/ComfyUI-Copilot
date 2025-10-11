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

    return new_config
