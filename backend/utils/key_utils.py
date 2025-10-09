

def workflow_config_adapt(config: dict):
    if config:
        if config.get("workflow_llm_api_key"):
            config["openai_api_key"] = config.get("workflow_llm_api_key")
            config["workflow_llm_api_key"] = None
        if config.get("workflow_llm_base_url"):
            config["openai_base_url"] = config.get("workflow_llm_base_url")
            config["workflow_llm_base_url"] = None