# Link Agent Tools for ComfyUI Workflow Connection Analysis

import json
import time
from typing import Dict, Optional, List

from agents.tool import function_tool
from ..utils.request_context import get_session_id
from ..dao.workflow_table import get_workflow_data, save_workflow_data
from ..utils.comfy_gateway import get_object_info
from ..utils.logger import log

@function_tool
async def analyze_missing_connections(reason: str = "analyze") -> str:
    """
    分析工作流中缺失的连接，枚举所有可能的连接选项和所需的新节点。
    
    返回格式说明：
    - missing_connections: 缺失连接的详细列表，包含节点ID、输入名称、需要的数据类型等（仅包含required输入）
    - possible_connections: 现有节点可以提供的连接选项
    - universal_inputs: 可以接受任意输出类型的通用输入端口
    - optional_unconnected_inputs: 未连接的可选输入列表，包含节点ID、输入名称、配置信息等
    - required_new_nodes: 需要创建的新节点类型列表
    - connection_summary: 连接分析的统计摘要（包含optional输入的统计）
    """
    try:
        session_id = get_session_id()
        if not session_id:
            log.error("analyze_missing_connections: No session_id found in context")
            return json.dumps({"error": "No session_id found in context"})
        
        workflow_data = get_workflow_data(session_id)
        if not workflow_data:
            return json.dumps({"error": "No workflow data found for this session"})
        
        object_info = await get_object_info()
        
        analysis_result = {
            "missing_connections": [],
            "possible_connections": [],
            "universal_inputs": [],  # 可以连接任意输出的输入端口
            "optional_unconnected_inputs": [],  # 未连接的optional输入
            "required_new_nodes": [],
            "connection_summary": {
                "total_missing": 0,
                "auto_fixable": 0,
                "requires_new_nodes": 0,
                "universal_inputs_count": 0,
                "optional_unconnected_count": 0
            }
        }
        
        # 构建现有节点的输出映射
        available_outputs = {}
        for node_id, node_data in workflow_data.items():
            node_class = node_data.get("class_type")
            if node_class in object_info and "output" in object_info[node_class]:
                outputs = object_info[node_class]["output"]
                available_outputs[node_id] = {
                    "class_type": node_class,
                    "outputs": [(i, output_type) for i, output_type in enumerate(outputs)]
                }
        
        # 分析每个节点的缺失连接
        for node_id, node_data in workflow_data.items():
            node_class = node_data.get("class_type")
            if node_class not in object_info:
                continue
                
            node_info = object_info[node_class]
            if "input" not in node_info:
                continue
                
            required_inputs = node_info["input"].get("required", {})
            current_inputs = node_data.get("inputs", {})
            
            # 检查每个required input
            for input_name, input_config in required_inputs.items():
                if input_name not in current_inputs:
                    # 发现缺失的连接
                    missing_connection = {
                        "node_id": node_id,
                        "node_class": node_class,
                        "input_name": input_name,
                        "input_config": input_config,
                        "required": True
                    }
                    
                    # 分析输入类型
                    if isinstance(input_config, (list, tuple)) and len(input_config) > 0:
                        expected_types = input_config[0] if isinstance(input_config[0], list) else [input_config[0]]
                    
                    missing_connection["expected_types"] = expected_types
                    
                    # 检查是否是通用输入（可以接受任意类型）
                    is_universal_input = "*" in expected_types
                    
                    if is_universal_input:
                        # 这是一个通用输入端口，可以连接任意输出
                        universal_input = {
                            "node_id": node_id,
                            "node_class": node_class,
                            "input_name": input_name,
                            "input_config": input_config,
                            "can_connect_any_output": True
                        }
                        analysis_result["universal_inputs"].append(universal_input)
                        analysis_result["connection_summary"]["universal_inputs_count"] += 1
                        analysis_result["connection_summary"]["auto_fixable"] += 1
                        
                        # 对于通用输入，我们不列出所有可能的连接，而是标记为通用
                        missing_connection["possible_matches"] = "universal"
                        missing_connection["is_universal"] = True
                    else:
                        # 查找具体类型匹配的连接
                        possible_matches = []
                        for source_node_id, source_info in available_outputs.items():
                            if source_node_id == node_id:  # 不能连接自己
                                continue
                                
                            for output_index, output_type in source_info["outputs"]:
                                # 检查类型匹配（排除通用类型的情况）
                                type_match = (output_type in expected_types or output_type == "*")
                                
                                if type_match:
                                    possible_matches.append({
                                        "source_node_id": source_node_id,
                                        "source_class": source_info["class_type"],
                                        "output_index": output_index,
                                        "output_type": output_type,
                                        "match_confidence": "high" if output_type in expected_types else "medium"
                                    })
                        
                        missing_connection["possible_matches"] = possible_matches
                        missing_connection["is_universal"] = False
                        
                        # 如果有可能的匹配，添加到possible_connections
                        if possible_matches:
                            analysis_result["possible_connections"].extend([
                                {
                                    "target_node_id": node_id,
                                    "target_input": input_name,
                                    "source_node_id": match["source_node_id"],
                                    "source_output_index": match["output_index"],
                                    "connection": [match["source_node_id"], match["output_index"]],
                                    "confidence": match["match_confidence"],
                                    "types": {
                                        "expected": expected_types,
                                        "provided": match["output_type"]
                                    }
                                } for match in possible_matches
                            ])
                            analysis_result["connection_summary"]["auto_fixable"] += 1
                        else:
                            # 没有匹配的输出，需要新节点
                            analysis_result["connection_summary"]["requires_new_nodes"] += 1
                            
                            # 分析需要什么类型的节点
                            required_node_types = analyze_required_node_types(expected_types, object_info)
                            analysis_result["required_new_nodes"].extend([{
                                "for_node": node_id,
                                "for_input": input_name,
                                "expected_types": expected_types,
                                "suggested_node_types": required_node_types
                            }])
                    
                    analysis_result["missing_connections"].append(missing_connection)
            
            # 检查optional inputs (未连接的可选输入)
            optional_inputs = node_info["input"].get("optional", {})
            for input_name, input_config in optional_inputs.items():
                if input_name not in current_inputs:
                    # 发现未连接的optional输入
                    optional_unconnected = {
                        "node_id": node_id,
                        "node_class": node_class,
                        "input_name": input_name,
                        "input_config": input_config,
                        "required": False
                    }
                    
                    # 分析输入类型
                    if isinstance(input_config, (list, tuple)) and len(input_config) > 0:
                        expected_types = input_config[0] if isinstance(input_config[0], list) else [input_config[0]]
                    else:
                        expected_types = ["*"]  # 默认为通用类型
                    
                    optional_unconnected["expected_types"] = expected_types
                    
                    # 检查是否是通用输入（可以接受任意类型）
                    is_universal_input = "*" in expected_types
                    optional_unconnected["is_universal"] = is_universal_input
                    
                    analysis_result["optional_unconnected_inputs"].append(optional_unconnected)
        
        # 更新统计信息
        analysis_result["connection_summary"]["total_missing"] = len(analysis_result["missing_connections"])
        analysis_result["connection_summary"]["optional_unconnected_count"] = len(analysis_result["optional_unconnected_inputs"])
        
        log.info(f"analysis_result: {json.dumps(analysis_result, ensure_ascii=False)}")
        return json.dumps(analysis_result)
        
    except Exception as e:
        return json.dumps({"error": f"Failed to analyze missing connections: {str(e)}"})

def analyze_required_node_types(expected_types: List[str], object_info: Dict) -> List[Dict]:
    """分析需要什么类型的节点来提供指定的输出类型"""
    suggested_nodes = []
    
    # 常见类型到节点的映射
    type_to_nodes = {
        "MODEL": ["CheckpointLoaderSimple", "CheckpointLoader", "UNETLoader"],
        "CLIP": ["CheckpointLoaderSimple", "CheckpointLoader", "CLIPLoader"],
        "VAE": ["CheckpointLoaderSimple", "CheckpointLoader", "VAELoader"],
        "CONDITIONING": ["CLIPTextEncode"],
        "LATENT": ["EmptyLatentImage", "VAEEncode"],
        "IMAGE": ["LoadImage", "VAEDecode"],
        "MASK": ["LoadImageMask"],
        "CONTROL_NET": ["ControlNetLoader"],
        "LORA": ["LoraLoader"],
        "IPADAPTER": ["IPAdapterModelLoader"]
    }
    
    for expected_type in expected_types:
        if expected_type in type_to_nodes:
            for node_class in type_to_nodes[expected_type]:
                if node_class in object_info:
                    suggested_nodes.append({
                        "node_class": node_class,
                        "output_type": expected_type,
                        "confidence": "high",
                        "description": f"{node_class} can provide {expected_type}"
                    })
        else:
            # 搜索所有能提供该类型输出的节点
            for node_class, node_info in object_info.items():
                if "output" in node_info:
                    outputs = node_info["output"]
                    if expected_type in outputs:
                        suggested_nodes.append({
                            "node_class": node_class,
                            "output_type": expected_type,
                            "confidence": "medium",
                            "description": f"{node_class} can provide {expected_type}"
                        })
    
    # 去重并排序
    unique_nodes = {}
    for node in suggested_nodes:
        key = node["node_class"]
        if key not in unique_nodes or unique_nodes[key]["confidence"] == "medium":
            unique_nodes[key] = node
    
    return list(unique_nodes.values())

def save_checkpoint_before_link_modification(session_id: str, action_description: str) -> Optional[int]:
    """在连接修改前保存checkpoint"""
    try:
        current_workflow = get_workflow_data(session_id)
        if not current_workflow:
            return None
            
        checkpoint_id = save_workflow_data(
            session_id,
            current_workflow,
            workflow_data_ui=None,
            attributes={
                "checkpoint_type": "link_agent_start",
                "description": f"Checkpoint before {action_description}",
                "action": "link_agent_checkpoint",
                "timestamp": time.time()
            }
        )
        log.info(f"Saved link agent checkpoint with ID: {checkpoint_id}")
        return checkpoint_id
    except Exception as e:
        log.error(f"Failed to save checkpoint before link modification: {str(e)}")
        return None 

@function_tool
def apply_connection_fixes(fixes_json: str) -> str:
    """批量应用连接修复，fixes_json应为包含修复指令的JSON字符串"""
    try:
        session_id = get_session_id()
        if not session_id:
            log.error("apply_connection_fixes: No session_id found in context")
            return json.dumps({"error": "No session_id found in context"})
        
        # 在修改前保存checkpoint
        checkpoint_id = save_checkpoint_before_link_modification(session_id, "batch connection fixes")
        
        # 解析修复指令
        fixes = json.loads(fixes_json) if isinstance(fixes_json, str) else fixes_json
        
        workflow_data = get_workflow_data(session_id)
        if not workflow_data:
            return json.dumps({"error": "No workflow data found for this session"})
        
        applied_fixes = []
        failed_fixes = []
        
        # 处理连接修复
        connections_to_add = fixes.get("connections", [])
        for conn_fix in connections_to_add:
            try:
                target_node_id = conn_fix["target_node_id"]
                target_input = conn_fix["target_input"]
                source_node_id = conn_fix["source_node_id"]
                source_output_index = conn_fix["source_output_index"]
                
                if target_node_id not in workflow_data:
                    failed_fixes.append({
                        "type": "connection",
                        "target": f"{target_node_id}.{target_input}",
                        "error": f"Target node {target_node_id} not found"
                    })
                    continue
                
                if source_node_id not in workflow_data:
                    failed_fixes.append({
                        "type": "connection", 
                        "target": f"{target_node_id}.{target_input}",
                        "error": f"Source node {source_node_id} not found"
                    })
                    continue
                
                # 应用连接
                if "inputs" not in workflow_data[target_node_id]:
                    workflow_data[target_node_id]["inputs"] = {}
                
                old_value = workflow_data[target_node_id]["inputs"].get(target_input, "not connected")
                new_connection = [source_node_id, source_output_index]
                workflow_data[target_node_id]["inputs"][target_input] = new_connection
                
                applied_fixes.append({
                    "type": "connection",
                    "target": f"{target_node_id}.{target_input}",
                    "source": f"{source_node_id}[{source_output_index}]",
                    "old_value": old_value,
                    "new_value": new_connection
                })
                
            except Exception as e:
                failed_fixes.append({
                    "type": "connection",
                    "target": f"{conn_fix.get('target_node_id', 'unknown')}.{conn_fix.get('target_input', 'unknown')}",
                    "error": str(e)
                })
        
        # 处理新节点添加
        nodes_to_add = fixes.get("new_nodes", [])
        for node_spec in nodes_to_add:
            try:
                node_class = node_spec["node_class"]
                node_id = node_spec.get("node_id", "")
                inputs = node_spec.get("inputs", {})
                
                # 生成节点ID
                if not node_id:
                    existing_ids = set(workflow_data.keys())
                    node_id = "1"
                    while node_id in existing_ids:
                        node_id = str(int(node_id) + 1)
                
                # 创建新节点
                new_node = {
                    "class_type": node_class,
                    "inputs": inputs,
                    "_meta": {"title": node_class}
                }
                
                workflow_data[node_id] = new_node
                
                applied_fixes.append({
                    "type": "add_node",
                    "node_id": node_id,
                    "node_class": node_class,
                    "inputs": inputs
                })
                
                # 如果指定了要自动连接的目标，进行连接
                auto_connect = node_spec.get("auto_connect", [])
                for auto_conn in auto_connect:
                    target_node_id = auto_conn["target_node_id"]
                    target_input = auto_conn["target_input"]
                    output_index = auto_conn.get("output_index", 0)
                    
                    if target_node_id in workflow_data:
                        if "inputs" not in workflow_data[target_node_id]:
                            workflow_data[target_node_id]["inputs"] = {}
                        
                        workflow_data[target_node_id]["inputs"][target_input] = [node_id, output_index]
                        
                        applied_fixes.append({
                            "type": "auto_connection",
                            "from_new_node": node_id,
                            "to": f"{target_node_id}.{target_input}",
                            "output_index": output_index
                        })
                
            except Exception as e:
                failed_fixes.append({
                    "type": "add_node",
                    "node_class": node_spec.get("node_class", "unknown"),
                    "error": str(e)
                })
        
        # 保存更新的工作流
        version_id = save_workflow_data(
            session_id,
            workflow_data,
            attributes={
                "action": "link_agent_batch_fix",
                "description": f"Applied {len(applied_fixes)} connection fixes",
                "fixes_applied": applied_fixes,
                "fixes_failed": failed_fixes
            }
        )
        
        # 构建返回数据，包含checkpoint信息
        ext_data = [{
            "type": "workflow_update",
            "data": {
                "workflow_data": workflow_data,
                "changes": {
                    "applied_fixes": applied_fixes,
                    "failed_fixes": failed_fixes
                }
            }
        }]
        
        # 如果成功保存了checkpoint，添加修改前的checkpoint信息
        if checkpoint_id:
            ext_data.append({
                "type": "link_agent_checkpoint",
                "data": {
                    "checkpoint_id": checkpoint_id,
                    "checkpoint_type": "link_agent_start"
                }
            })
        
        # 添加修改后的版本信息
        ext_data.append({
            "type": "link_agent_complete",
            "data": {
                "version_id": version_id,
                "checkpoint_type": "link_agent_complete"
            }
        })
        
        return json.dumps({
            "success": True,
            "version_id": version_id,
            "applied_fixes": applied_fixes,
            "failed_fixes": failed_fixes,
            "summary": {
                "total_fixes": len(applied_fixes),
                "failed_fixes": len(failed_fixes),
                "connections_added": len([f for f in applied_fixes if f["type"] == "connection"]),
                "nodes_added": len([f for f in applied_fixes if f["type"] == "add_node"])
            },
            "message": f"Applied {len(applied_fixes)} fixes successfully, {len(failed_fixes)} failed",
            "ext": ext_data
        })
        
    except Exception as e:
        return json.dumps({"error": f"Failed to apply connection fixes: {str(e)}"}) 