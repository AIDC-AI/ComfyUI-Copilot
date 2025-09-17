import json

from agents.tool import function_tool
from ..utils.modelscope_gateway import ModelScopeGateway
from ..utils.request_context import get_session_id

from ..utils.comfy_gateway import get_object_info_by_class
from ..dao.workflow_table import get_workflow_data, save_workflow_data
from ..utils.logger import log

async def get_node_parameters(node_name: str, param_name: str = "") -> str:
    """获取节点的参数信息，如果param_name为空则返回所有参数"""
    try:
        node_info_dict = await get_object_info_by_class(node_name)
        if not node_info_dict or node_name not in node_info_dict:
            return json.dumps({"error": f"Node '{node_name}' not found"})
        
        node_info = node_info_dict[node_name]
        if 'input' not in node_info:
            return json.dumps({"error": f"Node '{node_name}' has no input parameters"})
        
        input_params = node_info['input']
        
        if param_name:
            # 检查特定参数
            if input_params.get('required') and param_name in input_params['required']:
                return json.dumps({
                    "parameter": param_name,
                    "type": "required",
                    "config": input_params['required'][param_name]
                })
            
            if input_params.get('optional') and param_name in input_params['optional']:
                return json.dumps({
                    "parameter": param_name,
                    "type": "optional", 
                    "config": input_params['optional'][param_name]
                })
            
            return json.dumps({"error": f"Parameter '{param_name}' not found in node '{node_name}'"})
        else:
            # 返回所有参数
            return json.dumps({
                "node": node_name,
                "required": input_params.get('required', {}),
                "optional": input_params.get('optional', {})
            })
    
    except Exception as e:
        return json.dumps({"error": f"Failed to get node parameters: {str(e)}"})

@function_tool
async def find_matching_parameter_value(node_name: str, param_name: str, current_value: str, error_info: str = "") -> str:
    """根据错误信息找到匹配的参数值，支持多种参数类型的智能处理"""
    try:
        # 获取参数配置
        param_info_str = await get_node_parameters(node_name, param_name)
        param_info = json.loads(param_info_str)
        
        if "error" in param_info:
            return json.dumps(param_info)
        
        param_config = param_info.get("config", [])
        error_lower = error_info.lower()
        
        # 检查错误类型并提供相应处理策略
        error_analysis = {
            "error_type": "unknown",
            "is_model_related": False,
            "is_file_related": False,
        }
        
        # 优先识别image文件相关错误（在model检测之前，因为image文件可能包含model关键词）
        if (any(img_ext in current_value.lower() for img_ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"]) or
              param_name.lower() in ["image", "img", "picture", "photo"] or
              any(img_keyword in error_lower for img_keyword in ["invalid image", "image file", "image not found"])):
            error_analysis["error_type"] = "image_file_missing"
            error_analysis["is_file_related"] = True
            error_analysis["can_auto_fix"] = True
            
            # 如果参数配置是列表，查找其他可用的图片
            if isinstance(param_config, list) and len(param_config) > 0 and param_config[0]:
                available_images = [img for img in param_config[0] if any(ext in str(img).lower() for ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"])]
                
                if available_images:
                    # 随机选择一张可用图片
                    import random
                    recommended_image = random.choice(available_images)
                    return json.dumps({
                        "found_match": True,
                        "error_type": "image_file_missing",
                        "solution_type": "auto_replace",
                        "recommended_value": recommended_image,
                        "match_type": "image_replacement",
                        "message": f"Replaced missing image '{current_value}' with available image '{recommended_image}'",
                        "can_auto_fix": True,
                        "next_action": "update_parameter"
                    })
            
            return json.dumps({
                "found_match": False,
                "error_type": "image_file_missing",
                "solution_type": "manual_fix",
                "message": f"Missing image file: {current_value}",
                "suggestion": "Please add a valid image file to your ComfyUI input folder or choose an existing one",
                "can_auto_fix": False
            })
        
        # 识别model相关错误（在image检测之后）
        elif (any(model_keyword in current_value.lower() for model_keyword in [
            ".ckpt", ".safetensors", ".pt", ".pth", ".bin", "checkpoint", "lora", "vae", "controlnet", "clip", "unet"
        ]) or any(model_keyword in param_name.lower() for model_keyword in [
            "model", "checkpoint", "lora", "vae", "clip", "controlnet", "unet"
        ]) or any(model_keyword in error_lower for model_keyword in [
            "model not found", "checkpoint", "missing model", "file not found"
        ])):
            error_analysis["error_type"] = "model_missing"
            error_analysis["is_model_related"] = True
            
            return json.dumps({
                "found_match": False,
                "error_type": "model_missing",
                "message": f"Missing model file: {current_value}",
                "recommendation": "Check for available model replacements, otherwise download required.",
                "next_action": "check_available_models_or_suggest_download",
                "details": {
                    "node_name": node_name,
                    "param_name": param_name,
                    "missing_file": current_value,
                    "is_model_related": True,
                    "param_config": param_config
                }
            })
        
        # 处理枚举类型的参数（原有逻辑，但增强）
        elif isinstance(param_config, list) and len(param_config) > 0:
            available_values = param_config
            error_analysis["error_type"] = "enum_value_mismatch"
            error_analysis["can_auto_fix"] = True
            
            # 改进的匹配算法
            current_lower = current_value.lower().replace("_", " ").replace("-", " ")
            
            # 1. 完全匹配
            for value in available_values:
                if current_value == value:
                    return json.dumps({
                        "found_match": True,
                        "recommended_value": value,
                        "match_type": "exact",
                        "error_type": "enum_value_mismatch",
                        "solution_type": "exact_match",
                        "can_auto_fix": True,
                        "all_available": available_values
                    })
            
            # 2. 忽略大小写和符号的匹配
            for value in available_values:
                value_lower = str(value).lower().replace("_", " ").replace("-", " ")
                if current_lower == value_lower:
                    return json.dumps({
                        "found_match": True,
                        "recommended_value": value,
                        "match_type": "case_insensitive",
                        "error_type": "enum_value_mismatch",
                        "solution_type": "auto_replace",
                        "message": f"Found case-insensitive match: '{current_value}' -> '{value}'",
                        "can_auto_fix": True,
                        "next_action": "update_parameter",
                        "all_available": available_values
                    })
            
            # 3. 包含关系匹配
            best_match = None
            best_score = 0
            
            for value in available_values:
                value_lower = str(value).lower()
                value_parts = value_lower.replace("_", " ").replace("-", " ").split()
                current_parts = current_lower.split()
                
                # 计算匹配分数
                score = 0
                for part in current_parts:
                    if any(part in vp or vp in part for vp in value_parts):
                        score += 1
                
                if score > best_score:
                    best_score = score
                    best_match = value
            
            if best_match and best_score > 0:
                return json.dumps({
                    "found_match": True,
                    "recommended_value": best_match,
                    "match_type": "partial",
                    "error_type": "enum_value_mismatch",
                    "solution_type": "auto_replace",
                    "match_score": best_score,
                    "message": f"Found partial match: '{current_value}' -> '{best_match}' (score: {best_score})",
                    "can_auto_fix": True,
                    "next_action": "update_parameter",
                    "all_available": available_values[:10],
                    "original_value": current_value
                })
            
            # 4. 没有匹配，但可以用第一个可用值替代
            return json.dumps({
                "found_match": False,
                "recommended_value": available_values[0] if available_values else None,
                "match_type": "no_match",
                "error_type": "enum_value_mismatch", 
                "solution_type": "default_replace",
                "message": f"No match found for '{current_value}'. Using default value '{available_values[0]}'",
                "can_auto_fix": True,
                "next_action": "update_parameter",
                "all_available": available_values[:10],
                "total_options": len(available_values),
                "original_value": current_value,
                "suggestion": f"No match found for '{current_value}'. Replacing with default option."
            })
        
        # 处理其他类型的参数
        else:
            error_analysis["error_type"] = "non_enum_parameter"
            error_analysis["can_auto_fix"] = False
            
            return json.dumps({
                "found_match": False,
                "error_type": "non_enum_parameter",
                "solution_type": "manual_fix",
                "parameter_type": type(param_config).__name__,
                "config": param_config,
                "can_auto_fix": False,
                "message": f"Parameter '{param_name}' is not an enumerable type",
                "suggestion": f"Parameter '{param_name}' requires manual configuration. Check the parameter requirements."
            })
        
    except Exception as e:
        return json.dumps({
            "error": f"Failed to find matching parameter value: {str(e)}",
            "can_auto_fix": False,
            "solution_type": "error"
        })

@function_tool
async def get_model_files(model_type: str = "checkpoints") -> str:
    """获取可用的模型文件列表"""
    try:
        # 定义模型类型到节点的映射
        model_type_mapping = {
            "checkpoints": ["CheckpointLoaderSimple", "CheckpointLoader"],
            "loras": ["LoraLoader", "LoraLoaderModelOnly"],
            "vae": ["VAELoader"],
            "clip": ["CLIPLoader", "DualCLIPLoader"],
            "controlnet": ["ControlNetLoader", "ControlNetApply"],
            "unet": ["UNETLoader"],
            "ipadapter": ["IPAdapterModelLoader"]
        }
        
        # 查找对应的节点
        model_files = {}
        for node_name in model_type_mapping.get(model_type.lower(), []):
            try:
                # 使用 get_object_info_by_class 获取单个节点信息，减少数据量
                node_data = await get_object_info_by_class(node_name)
                
                # 处理不同的返回格式
                node_info = None
                if node_name in node_data:
                    # 格式：{"NodeName": {...}}
                    node_info = node_data[node_name]
                elif 'input' in node_data:
                    # 格式：直接返回节点信息 {...}
                    node_info = node_data
                
                if node_info and 'input' in node_info:
                    # 查找包含文件列表的参数
                    for input_type in ['required', 'optional']:
                        if input_type in node_info['input']:
                            for param_name, param_config in node_info['input'][input_type].items():
                                # 检查参数配置格式：[file_list, {...}] 或 [file_list]
                                if isinstance(param_config, list) and len(param_config) > 0:
                                    if isinstance(param_config[0], list) and len(param_config[0]) > 0:
                                        # 检查是否为文件列表（包含文件扩展名或路径）
                                        file_list = param_config[0]
                                        if any(isinstance(item, str) and ('.' in item or '/' in item) for item in file_list):
                                            model_files[f"{node_name}.{param_name}"] = file_list
                            
            except Exception as e:
                # 单个节点查询失败，继续处理其他节点
                log.error(f"Failed to get info for node {node_name}: {e}")
                continue
        
        if model_files:
            return json.dumps({
                "model_type": model_type,
                "available_models": model_files
            })
        else:
            return json.dumps({
                "model_type": model_type,
                "available_models": {},
                "message": f"No {model_type} models found. Please check your ComfyUI models folder."
            })
        
    except Exception as e:
        return json.dumps({"error": f"Failed to get model files: {str(e)}"})


def suggest_model_download_by_modelscope(model_name_keyword: str) -> str:
    """建议下载缺失的模型，执行一次即可结束流程返回结果"""
    modelscope_gateway = ModelScopeGateway()
    return modelscope_gateway.suggest(name=model_name_keyword)


@function_tool
def suggest_model_download(models_list: str = "") -> str:
    """
    建议下载缺失的模型，执行一次即可结束流程返回结果，支持批量处理
    
    Args:
        models_list: 缺失模型列表的JSON字符串，格式为：
                    '[{"model_type":"checkpoints","missing_model":"model.safetensors","model_name_keyword":"sd"}]'
                    其中model_type: 模型类型，取值范围为checkpoints, clip, clip_vision, configs, controlnet, diffusers, diffusion_models, embeddings, gligen, hypernetworks, loras, photomaker, style_models, text_encoders, unet, upscale_models, vae, vae_approx
                    missing_model: 缺失的模型名称
                    model_name_keyword: 模型名称的关键词，用于模糊查询，短词优先，不要携带文件类型后缀
        
    Returns:
        str: 建议下载的模型列表json字符串

    """
    try:
        if not models_list or not models_list.strip():
            return json.dumps({"error": "models_list is required"})
        
        # 解析输入的模型列表
        try:
            # 尝试解析为列表
            if models_list.strip().startswith('['):
                models_data = json.loads(models_list)
            else:
                # 单个模型对象，转换为列表
                models_data = [json.loads(models_list)]
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON format: {str(e)}"})
        
        if not isinstance(models_data, list):
            return json.dumps({"error": "models_list should be a list or single model object"})
        
        # 存储所有模型建议结果
        all_model_suggestions = []
        missing_models_info = []
        failed_models = []
        
        # 遍历每个模型进行查询
        for model_item in models_data:
            if not isinstance(model_item, dict):
                failed_models.append({"model": str(model_item), "error": "Invalid model format"})
                continue
                
            model_type = model_item.get("model_type", "")
            missing_model = model_item.get("missing_model", "")
            model_name_keyword = model_item.get("model_name_keyword", "")
            
            if not model_type or not missing_model:
                failed_models.append({
                    "model": missing_model or "unknown", 
                    "error": "model_type and missing_model are required"
                })
                continue
            
            # 如果没有提供关键词，从模型名中提取
            if not (model_name_keyword and model_name_keyword.strip()):
                missing_model_parts = missing_model.split(".")
                if len(missing_model_parts) > 1:
                    model_name_keyword = missing_model_parts[0]
                else:
                    model_name_keyword = missing_model
            
            # 记录缺失模型信息
            missing_models_info.append({
                "model_type": model_type,
                "missing_model": missing_model,
                "model_name_keyword": model_name_keyword
            })
            
            # 优先使用modelscope检索模型
            try:
                result = suggest_model_download_by_modelscope(model_name_keyword)
                if result and result.get("data") and len(result.get("data")) > 0:
                    # 为每个结果添加上下文信息
                    for suggestion in result["data"]:
                        suggestion["source_model_type"] = model_type
                        suggestion["source_missing_model"] = missing_model
                        suggestion["source_keyword"] = model_name_keyword
                        for item in result["data"]:
                            item["source_model_type"] = model_type
                    all_model_suggestions.extend(result["data"])
                else:
                    # ModelScope没有找到结果，记录失败信息
                    failed_models.append({
                        "model": missing_model,
                        "model_type": model_type,
                        "keyword": model_name_keyword,
                        "error": "No models found in ModelScope"
                    })
            except Exception as e:
                failed_models.append({
                    "model": missing_model,
                    "model_type": model_type,
                    "keyword": model_name_keyword,
                    "error": f"ModelScope query failed: {str(e)}"
                })
        
        # 先按模型分组，每个模型取top3，然后再去重
        grouped_suggestions = {}
        for suggestion in all_model_suggestions:
            source_model = suggestion.get("source_missing_model", "unknown")
            if source_model not in grouped_suggestions:
                grouped_suggestions[source_model] = []
            grouped_suggestions[source_model].append(suggestion)
        
        # 每个模型取top3
        top3_per_model = []
        for model, suggestions in grouped_suggestions.items():
            suggestions_top3 = suggestions[:3]
            for item in suggestions_top3:
                item["model_type"] = model_type
            top3_per_model.extend(suggestions_top3)
        
        # 基于模型名称去重
        seen_models = set()
        unique_suggestions = []
        for suggestion in top3_per_model:
            # 使用Path和Name组合作为唯一标识
            model_id = f"{suggestion.get('Path', '')}/{suggestion.get('Name', '')}"
            if model_id not in seen_models:
                seen_models.add(model_id)
                unique_suggestions.append(suggestion)
        
        # 最终建议列表
        top_suggestions = unique_suggestions
        
        # 构建返回结果
        result = {
            "success": True,
            "total_requested": len(models_data),
            "found_suggestions": len(top_suggestions),
            "failed_count": len(failed_models),
            "missing_models": missing_models_info,
            "message": f"Found {len(top_suggestions)} model suggestions from ModelScope (top 3, deduplicated)",
            "ext": [{
                "type": "param_update",
                "data": {
                    "model_suggest": top_suggestions,
                    "failed_models": failed_models,
                    "summary": {
                        "total_requested": len(models_data),
                        "found_suggestions": len(top_suggestions),
                        "failed_count": len(failed_models)
                    }
                }
            }]
        }
        
        # 如果没有找到任何建议，添加兜底信息
        if not top_suggestions:
            result["fallback_message"] = "No models found in ModelScope. Consider manual download from Hugging Face or Civitai."
            result["general_suggestions"] = [
                "1. Check model names and keywords for typos",
                "2. Try broader keywords (e.g., 'stable-diffusion' instead of specific version)",
                "3. Download from Hugging Face: https://huggingface.co/models",
                "4. Download from Civitai: https://civitai.com/",
                "5. Place models in appropriate ComfyUI/models/ subfolders"
            ]
        
        return json.dumps(result)
    
    except Exception as e:
        return json.dumps({"error": f"Failed to suggest model download: {str(e)}"})

@function_tool
def update_workflow_parameter(node_id: str, param_name: str, new_value: str) -> str:
    """更新工作流中的特定参数"""
    try:
        session_id = get_session_id()
        if not session_id:
            log.error("update_workflow_parameter: No session_id found in context")
            return json.dumps({"error": "No session_id found in context"})
        
        # 获取当前工作流
        workflow_data = get_workflow_data(session_id)
        if not workflow_data:
            return json.dumps({"error": "No workflow data found for this session"})
        
        # 检查节点是否存在
        if node_id not in workflow_data:
            return json.dumps({"error": f"Node {node_id} not found in workflow"})
        
        # 更新参数
        if "inputs" not in workflow_data[node_id]:
            workflow_data[node_id]["inputs"] = {}
        
        old_value = workflow_data[node_id]["inputs"].get(param_name, "not set")
        workflow_data[node_id]["inputs"][param_name] = new_value
        
        # 保存更新的工作流到数据库
        save_workflow_data(
            session_id,
            workflow_data,
            workflow_data_ui=None,  # UI format not available here
            attributes={
                "action": "parameter_update", 
                "description": f"Updated {param_name} in node {node_id}",
                "changes": {
                    "node_id": node_id,
                    "parameter": param_name,
                    "old_value": old_value,
                    "new_value": new_value
                }
            }
        )
        
        return json.dumps({
            "success": True,
            "answer": f"Successfully updated {param_name} from '{old_value}' to '{new_value}' in node {node_id}",
            "node_id": node_id,
            "parameter": param_name,
            "old_value": old_value,
            "new_value": new_value,
            "message": f"Successfully updated {param_name} from '{old_value}' to '{new_value}' in node {node_id}",
            # 添加ext数据用于前端实时更新画布
            "ext": [{
                "type": "param_update",
                "data": {
                    "workflow_data": workflow_data,
                    "changes": [{  # 包装成数组格式，与前端MessageList期望的格式匹配
                        "node_id": node_id,
                        "parameter": param_name,
                        "old_value": old_value,
                        "new_value": new_value
                    }]
                }
            }]
        })
        
    except Exception as e:
        return json.dumps({"error": f"Failed to update workflow parameter: {str(e)}"})

