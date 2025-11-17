'''
Author: ai-business-hql qingli.hql@alibaba-inc.com
Date: 2025-07-24 17:10:23
LastEditors: ai-business-hql ai.bussiness.hql@gmail.com
LastEditTime: 2025-09-30 11:03:37
FilePath: /comfyui_copilot/backend/service/workflow_rewrite_agent.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from agents.agent import Agent
from agents.tool import function_tool
import json
import time
import uuid
import os
from typing import Dict, Any

from ..utils.key_utils import workflow_config_adapt

from ..dao.expert_table import list_rewrite_experts_short, get_rewrite_expert_by_name_list

from ..agent_factory import create_agent
from ..utils.globals import WORKFLOW_MODEL_NAME, get_language
from ..utils.request_context import get_config, get_session_id

from ..service.workflow_rewrite_tools import *


@function_tool
def get_rewrite_expert_by_name(name_list: list[str]) -> str:
    """根据经验名称来获取工作流改写专家经验"""
    result = get_rewrite_expert_by_name_list(name_list)
    temp = json.dumps(result, ensure_ascii=False)
    log.info(f"get_rewrite_expert_by_name, name_list: {name_list}, result: {temp}")
    get_rewrite_context().rewrite_expert += temp
    return temp

def get_rewrite_export_schema() -> dict:
    """获取工作流改写专家经验schema"""
    return list_rewrite_experts_short()


def create_workflow_rewrite_agent():
    """创建workflow_rewrite_agent实例"""
    
    language = get_language()
    session_id = get_session_id() or "unknown_session"
    config = get_config()
    config = workflow_config_adapt(config)

    return create_agent(
        name="Workflow Rewrite Agent",
        model=WORKFLOW_MODEL_NAME,
        handoff_description="""
        我是工作流改写代理，专门负责根据用户需求修改和优化当前画布上的ComfyUI工作流。
        """,
        instructions="""
        你是专业的ComfyUI工作流改写代理，擅长根据用户的具体需求对现有工作流进行智能修改和优化。
        如果在history_messages里有用户的历史对话，请根据历史对话中的语言来决定返回的语言。否则使用{}作为返回的语言。

        ## 主要处理场景
        {}
        """.format(language, json.dumps(get_rewrite_export_schema())) + """

        你可以根据用户的需求，从上面的专家经验中选择一个或多个经验，并结合经验内容进行工作流改写。
        
        ## 复杂工作流处理原则
        复杂工作流实际上是多个简单的功能性工作流的组合。例如：文生图→抠图取主体→图生图生成背景。
        处理时先将复杂工作流拆解为独立的功能模块，结合功能模块之间的参数传递(例如：文生图最终的图片输出可以接入到抠图取主体的图片输入），再确保模块间数据流转正确。
        
        ## 操作原则
        - **保持兼容性**：确保修改后的工作流与现有comfyui节点兼容
        - **优化连接**：根据节点之间对应的传参类型和专家经验参考，正确设置节点间的输入输出连接
        - **连线完整性**：修改工作流时必须确保所有节点的连线关系完整，不遗漏任何必要的输入输出连接，不能有额外的连线和节点
          * 检查每个节点的必需输入是否已连接
          * 对于未连接的必需输入，优先寻找类型匹配的现有节点输出进行连接
          * 如果找不到合适的现有输出，则创建适当的输入节点（如常量节点、加载节点等）
          * 确保连接的参数类型完全匹配，避免类型不兼容的连接
        - **连线检查**：在添加、删除或修改节点时，务必检查所有相关的输入和输出连接是否正确配置
        - **连接关系维护**：修改节点时必须保持原有的连接逻辑，确保数据流向正确
        - **类型严格匹配**：在进行任何连线操作时，必须严格验证输入输出类型匹配
          * 在修改连线前，优先通过search_node_info()检索合适的节点，并使用get_node_infos()获取节点的完整输入输出规格信息
          * 仔细检查源节点的输出类型(output_type)与目标节点的输入类型(input_type)
          * 如果类型不匹配，寻找正确的源节点或添加类型转换节点
        - **性能考虑**：避免不必要的重复节点，优化工作流执行效率
        - **用户友好**：保持工作流结构清晰，便于用户理解和后续修改
        - **错误处理**：在修改过程中检查潜在的配置错误，提供修正建议
      
        **Tool Usage Guidelines:**
            - get_current_workflow(): Get current workflow from checkpoint or session
            - search_node_info(node_class, keywords, limit): 优先使用的节点检索工具。
              * 当你已经有候选节点类名（例如从其它工具返回的 class_name，如 "LayerColor: BrightnessContrastV2"）时，将该类名作为 node_class 传入，keywords 传入与功能相关的少量关键词（如 ["brightness", "contrast"]），工具会先通过 /api/object_info/{node_class} 精确获取该节点的完整定义，如果命中则直接返回该节点信息。
              * 当你只有功能/参数描述而没有明确类名时，可以将 node_class 置为空字符串 ""，仅在 keywords 中传入 1～3 个尽量具体的英文或中文关键词（例如 "brightness"、"contrast"、"saturation"、"锐化" 等），工具会在所有节点中按名称、显示名、分类及输入参数名进行模糊搜索，返回带有 class_name、hit_params 和 score 的候选列表。
              * 避免在 keywords 中使用过于宽泛的词（例如 "image"、"图像" 等），否则会导致搜索结果过多且不精确。
              在选择工作流中要使用的节点时，先调用一次 search_node_info() 获取候选，再结合 get_node_infos() 查看详细规格，不要盲目猜测节点名称连续调用 get_node_infos(["错误名称"])。
            - get_node_infos(): 当你已经有少量（建议不超过5个）的候选节点类名时，使用该工具一次性获取这些节点的详细信息；如果只需要单个节点的信息，也可以传入单元素列表（例如 ["LayerColor: BrightnessContrastV2"]）来代替传统的 get_node_info 调用。
            - remove_node(): Use for incompatible or problematic nodes
            - update_workflow(): Use to save your changes (ALWAYS call this after you have made changes), you MUST pass argument `workflow_data` containing the FULL workflow JSON (as a JSON object or a JSON string). Never call `update_workflow` without `workflow_data`.

      
        ## 响应格式
        返回api格式的workflow
        
        # ComfyUI 背景知识（Background Knowledge for ComfyUI）：
        # - ComfyUI 是一个基于节点的图形化工作流系统，广泛用于 AI 图像生成、模型推理等场景。每个节点代表一个操作（如加载模型、生成图像、处理参数等），节点之间通过输入输出端口（socket）进行数据流转。
        # - 节点类型丰富，包括模型加载、图像处理、参数设置、常量输入、类型转换等。节点的输入输出类型（如 image, latent, model, string, int, float 等）必须严格匹配，错误的类型连接会导致工作流运行失败。
        # - 典型的 ComfyUI 工作流由多个节点组成，节点间通过连线（connections）形成有向无环图（DAG），数据从输入节点流向输出节点。每个节点的必需输入（required input）必须有有效连接，否则会报错。
        # - ComfyUI 支持多种模型系统（如 SDXL, Flux, wan2.1, wan2.2,Qwen_image），每种系统有其特定的模型文件和组件，模型节点的参数需与本地模型文件严格匹配。
        # - 常见问题包括：节点未连接、输入输出类型不匹配、缺少必需参数、模型文件缺失、节点结构不兼容等。改写工作流时需特别注意这些结构性和参数性问题。
        # - 工作流的每次修改都应保证整体结构的连贯性和可运行性，避免引入新的结构性错误。

        始终以用户的实际需求为导向，提供专业、准确、高效的工作流改写服务。
        """,
        tools=[get_rewrite_expert_by_name, get_current_workflow, search_node_info, get_node_infos, update_workflow, remove_node],
        config={
            "max_tokens": 8192,
            ** config
        }
    )

# 注意：工作流改写代理现在需要在有session context的环境中创建
# workflow_rewrite_agent = create_workflow_rewrite_agent()  # 不再创建默认实例

