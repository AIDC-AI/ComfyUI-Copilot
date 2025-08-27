from server import PromptServer
from aiohttp import web
from typing import Dict, Any
import logging
from ..dao.expert_table import (
    create_rewrite_expert,
    get_rewrite_expert,
    list_rewrite_experts,
    update_rewrite_expert_by_id,
    delete_rewrite_expert_by_id
)

# 配置日志
logger = logging.getLogger(__name__)

def validate_expert_data(data: Dict[str, Any]) -> tuple[bool, str, Dict[str, Any]]:
    """验证专家数据"""
    if not data:
        return False, "请求数据不能为空", {}
    
    # 验证必填字段
    if 'name' not in data or not data['name']:
        return False, "名称不能为空", {}
    
    # 验证字段类型和长度
    if not isinstance(data['name'], str) or len(data['name']) > 255:
        return False, "名称必须是字符串且长度不超过255个字符", {}
    
    # 验证可选字段
    validated_data = {
        'name': data['name'].strip(),
        'description': data.get('description'),
        'content': data.get('content')
    }
    
    return True, "", validated_data

@PromptServer.instance.routes.post("/api/expert/experts")
async def create_expert(request):
    """创建新的专家记录"""
    try:
        data = await request.json()
        if not data:
            return web.json_response({"success": False, "message": "请求数据格式错误", "data": None}, status=400)
        
        # 验证数据
        is_valid, error_msg, validated_data = validate_expert_data(data)
        if not is_valid:
            return web.json_response({"success": False, "message": error_msg, "data": None}, status=400)
        
        # 创建专家记录
        expert_id = create_rewrite_expert(
            name=validated_data['name'],
            description=validated_data['description'],
            content=validated_data['content']
        )
        
        logger.info(f"成功创建专家记录，ID: {expert_id}")
        
        return web.json_response({"success": True, "message": "创建成功", "data": {"id": expert_id}}, status=200)
        
    except Exception as e:
        logger.error(f"创建专家记录失败: {str(e)}")
        return web.json_response({"success": False, "message": f"创建失败: {str(e)}", "data": None}, status=500)

@PromptServer.instance.routes.get("/api/expert/experts")
async def get_experts(request):
    """获取所有专家记录列表"""
    try:
        experts = list_rewrite_experts()
        
        logger.info(f"成功获取专家记录列表，共 {len(experts)} 条")
        
        return web.json_response({"success": True, "message": "获取列表成功", "data": {"total": len(experts), "experts": experts}}, status=200)
        
    except Exception as e:
        logger.error(f"获取专家记录列表失败: {str(e)}")
        return web.json_response({"success": False, "message": f"获取列表失败: {str(e)}", "data": None}, status=500)

@PromptServer.instance.routes.get("/api/expert/experts/{expert_id}")
async def get_expert_by_id(request):
    """根据ID获取专家记录"""
    try:
        expert_id = int(request.match_info['expert_id'])
        expert = get_rewrite_expert(expert_id)
        
        if not expert:
            return web.json_response({"success": False, "message": "ID不存在", "data": None}, status=404)
        
        logger.info(f"成功获取专家记录，ID: {expert_id}")
        
        return web.json_response({"success": True, "message": "获取记录成功", "data": expert}, status=200)
        
    except Exception as e:
        logger.error(f"获取专家记录失败，ID: {expert_id}, 错误: {str(e)}")
        return web.json_response({"success": False, "message": f"获取记录失败: {str(e)}", "data": None}, status=500)

@PromptServer.instance.routes.put("/api/expert/experts/{expert_id}")
async def update_expert(request):
    """更新专家记录"""
    try:
        expert_id = int(request.match_info['expert_id'])
        data = await request.json()
        if not data:
            return web.json_response({"success": False, "message": "请求数据格式错误", "data": None}, status=400)
        
        # 验证数据
        is_valid, error_msg, validated_data = validate_expert_data(data)
        if not is_valid:
            return web.json_response({"success": False, "message": error_msg, "data": None}, status=400)
        
        # 更新专家记录
        success = update_rewrite_expert_by_id(
            expert_id=expert_id,
            name=validated_data.get('name'),
            description=validated_data.get('description'),
            content=validated_data.get('content')
        )
        
        if not success:
            return web.json_response({"success": False, "message": "ID不存在", "data": None}, status=404)
        
        logger.info(f"成功更新专家记录，ID: {expert_id}")
        
        return web.json_response({"success": True, "message": "更新成功", "data": {"id": expert_id}}, status=200)
        
    except Exception as e:
        logger.error(f"更新专家记录失败，ID: {expert_id}, 错误: {str(e)}")
        return web.json_response({"success": False, "message": f"更新失败: {str(e)}", "data": None}, status=500)

@PromptServer.instance.routes.delete("/api/expert/experts/{expert_id}")
async def delete_expert(request):
    """删除专家记录"""
    try:
        expert_id = int(request.match_info['expert_id'])
        success = delete_rewrite_expert_by_id(expert_id)
        
        if not success:
            return web.json_response({"success": False, "message": "ID不存在", "data": None}, status=404)
        
        logger.info(f"成功删除专家记录，ID: {expert_id}")
        
        return web.json_response({"success": True, "message": "删除成功", "data": {"id": expert_id}}, status=200)
        
    except Exception as e:
        logger.error(f"删除专家记录失败，ID: {expert_id}, 错误: {str(e)}")
        return web.json_response({"success": False, "message": f"删除失败: {str(e)}", "data": None}, status=500)

@PromptServer.instance.routes.patch("/api/expert/experts/{expert_id}")
async def partial_update_expert(request):
    """部分更新专家记录"""
    try:
        expert_id = int(request.match_info['expert_id'])
        data = await request.json()
        if not data:
            return web.json_response({"success": False, "message": "请求数据格式错误", "data": None}, status=400)
        
        # 验证字段
        update_data = {}
        if 'name' in data:
            if not isinstance(data['name'], str) or len(data['name']) > 255:
                return web.json_response({"success": False, "message": "名称必须是字符串且长度不超过255个字符", "data": None}, status=400)
            update_data['name'] = data['name'].strip()
        
        if 'description' in data:
            update_data['description'] = data['description']
        
        if 'content' in data:
            update_data['content'] = data['content']
        
        if not update_data:
            return web.json_response({"success": False, "message": "没有提供要更新的字段", "data": None}, status=400)
        
        # 更新专家记录
        success = update_rewrite_expert_by_id(
            expert_id=expert_id,
            **update_data
        )
        
        if not success:
            return web.json_response({"success": False, "message": "ID不存在", "data": None}, status=404)
        
        logger.info(f"成功部分更新专家记录，ID: {expert_id}")
        
        return web.json_response({"success": True, "message": "更新成功", "data": {"id": expert_id}}, status=200)
        
    except Exception as e:
        logger.error(f"部分更新专家记录失败，ID: {expert_id}, 错误: {str(e)}")
        return web.json_response({"success": False, "message": f"更新失败: {str(e)}", "data": None}, status=500)

# 路由配置函数
# 所有路由已通过装饰器自动注册到 ComfyUI 的 PromptServer
