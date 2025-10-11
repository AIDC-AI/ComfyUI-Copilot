'''
Author: ai-business-hql ai.bussiness.hql@gmail.com
Date: 2025-08-25 20:16:18
LastEditors: ai-business-hql ai.bussiness.hql@gmail.com
LastEditTime: 2025-08-28 11:16:40
FilePath: /ComfyUI-Copilot/backend/service/workflow_rewrite_agent_simple.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''

import json
from typing import Dict, Any, Optional
import asyncio
from pydantic import BaseModel
from ..utils.key_utils import workflow_config_adapt
from openai import OpenAI

from ..agent_factory import create_agent
from ..utils.globals import WORKFLOW_MODEL_NAME, get_comfyui_copilot_api_key, LLM_DEFAULT_BASE_URL
from ..utils.request_context import get_config, get_rewrite_context, RewriteContext
from ..utils.logger import log


class RewriteResponse(BaseModel):
    """
    重写后的工作流数据，必须是严格的JSON字符串
    """
    workflow_data: str

def rewrite_workflow_simple(rewrite_context: RewriteContext) -> str:
    """
    使用简化的方式重写工作流，直接调用OpenAI API
    
    Args:
        rewrite_context: 包含所有重写所需信息的上下文
        
    Returns:
        改写后的API工作流(JSON字符串)
    """
    try:
        # 构建给LLM的完整上下文信息
        context_info = f"""
## 重写意图
{rewrite_context.rewrite_intent}

## 当前工作流 (ComfyUI API格式)
{rewrite_context.current_workflow}

## 节点信息
{json.dumps(rewrite_context.node_infos or {}, ensure_ascii=False)}

## 专家经验
{rewrite_context.rewrite_expert or "无特定专家经验"}
"""

        # 构建系统提示词
        system_prompt = """你是专业的ComfyUI工作流重写专家。你需要根据用户的重写意图，对现有的ComfyUI API格式工作流进行改写。

## ComfyUI工作流基础知识
- ComfyUI工作流是基于节点的图形化系统，每个节点代表一个操作
- 节点通过输入输出端口进行数据流转，形成有向无环图(DAG)
- 节点的输入输出类型必须严格匹配(如image, latent, model, string, int, float等)
- 每个节点的必需输入必须有有效连接，否则会导致工作流运行失败

## API格式结构
ComfyUI API格式工作流是一个JSON对象，其中：
- 键是节点ID (字符串形式的数字，如"1", "2", "3")
- 值是节点对象，包含：
  - class_type: 节点类型
  - inputs: 输入参数对象，可以是：
    - 直接值(字符串、数字等)
    - 连接引用 [node_id, output_index] 形式的数组

## 重写原则
1. **保持结构完整性**：确保所有节点的必需输入都有连接
2. **类型匹配**：输入输出类型必须严格匹配
3. **连接正确性**：确保节点间的连接关系正确，不要有参数类型不匹配的链接
4. **功能实现**：确保改写后的工作流能正常运行且实现用户的重写意图

## 重要：输出格式要求
你必须严格按照以下JSON格式返回结果，不要添加任何其他说明文字：
{
  "workflow_data": "这里是完整的工作流JSON字符串"
}
"""
        config = get_config()
<<<<<<< HEAD
        config = workflow_config_adapt(config)
=======
        workflow_config_adapt(config)
>>>>>>> main
        # 创建OpenAI客户端
        client = OpenAI(
            base_url = config.get("openai_base_url") or LLM_DEFAULT_BASE_URL,
            api_key = config.get("openai_api_key") or get_comfyui_copilot_api_key() or ""
        )

        # 调用LLM
        completion = client.chat.completions.parse(
            model=WORKFLOW_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context_info}
            ],
            max_tokens=8192,
            temperature=0.1,  # 降低随机性，确保输出一致性
            response_format=RewriteResponse  # 要求返回JSON格式
        )

        result = completion.choices[0].message.parsed
        log.info(f"workflow simple rewrite LLM response: {result}")

        # 解析返回的JSON
        # result = json.loads(result_text)
        
        # 验证返回格式
        if result.workflow_data is None:
            return "{}"
        
        # 验证workflow_data是有效的JSON字符串
        if isinstance(result.workflow_data, str):
            # 尝试解析以验证有效性
            json.loads(result.workflow_data)
            return result.workflow_data
        else:
            # 如果不是字符串，转换为字符串
            return json.dumps(result.workflow_data, ensure_ascii=False)

    except Exception as e:
        log.error(f"简化工作流重写失败: {str(e)}")
        return f"工作流重写失败:{str(e)}"