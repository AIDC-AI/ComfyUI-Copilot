'''
Author: ai-business-hql ai.bussiness.hql@gmail.com
Date: 2025-11-19
LastEditors: ai-business-hql ai.bussiness.hql@gmail.com
LastEditTime: 2025-11-19
FilePath: /ComfyUI-Copilot/backend/service/message_memory.py
Description: Message memory manager with automatic compression
'''

from typing import List, Dict, Any, Tuple
from ..dao.session_message_table import (
    get_session_message,
    save_session_message,
    update_summary
)
from .summary_agent import generate_summary
from ..utils.logger import log


# 配置参数
COMPRESSION_THRESHOLD = 8  # 超过10条未压缩消息时触发压缩（4个来回）
KEEP_RECENT_MESSAGES = 4   # 保留最新4条消息不压缩（2个来回）


def message_memory_optimize(
    session_id: str, 
    messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    优化消息内存，自动压缩历史消息
    
    工作流程：
    1. 加载 session 数据（如果不存在则创建）
    2. 更新完整的消息列表
    3. 检查是否需要压缩（未压缩消息 > 10条）
    4. 如果需要，执行压缩并更新数据库
    5. 返回优化后的消息列表（summary + 未压缩的消息）
    
    Args:
        session_id: 会话ID
        messages: 当前的完整消息列表
        
    Returns:
        优化后的消息列表，可以直接传给 LLM
        - 如果有压缩：[{"role": "system", "content": "Previous summary: ..."}, ...recent_messages]
        - 如果无压缩：原始 messages
    """
    try:
        log.info(f"[Memory] Starting memory optimization for session: {session_id}")
        log.info(f"[Memory] Input messages count: {len(messages)}")
        
        # 1. 加载或创建 session 记录
        record = get_session_message(session_id)
        
        if record is None:
            # 首次访问，创建新记录
            log.info(f"[Memory] New session detected, creating record")
            save_session_message(
                session_id=session_id,
                messages=messages,
                index=0,
                summary=None
            )
            # 新会话不需要压缩，直接返回原始消息
            return messages
        
        # 2. 更新消息列表（保存当前完整的消息）
        current_index = record['index']
        current_summary = record['summary']
        
        log.info(f"[Memory] Existing session - index: {current_index}, summary length: {len(current_summary) if current_summary else 0}")
        
        # 保存更新后的完整消息列表
        save_session_message(
            session_id=session_id,
            messages=messages,
            index=current_index,  # 暂时保持不变
            summary=current_summary
        )
        
        # 3. 检查是否需要压缩
        uncompressed_count = len(messages) - current_index
        log.info(f"[Memory] Uncompressed messages: {uncompressed_count} (threshold: {COMPRESSION_THRESHOLD})")
        
        if uncompressed_count <= COMPRESSION_THRESHOLD:
            # 不需要压缩，构建返回消息
            log.info(f"[Memory] No compression needed")
            return _build_optimized_messages(current_summary, messages, current_index)
        
        # 4. 执行压缩
        log.info(f"[Memory] Compression triggered!")
        
        # 计算压缩范围
        # 待压缩：messages[current_index : len(messages) - KEEP_RECENT_MESSAGES]
        compress_end_index = len(messages) - KEEP_RECENT_MESSAGES
        messages_to_compress = messages[current_index:compress_end_index]
        
        log.info(f"[Memory] Compressing messages from index {current_index} to {compress_end_index}")
        log.info(f"[Memory] Messages to compress: {len(messages_to_compress)}")
        
        # 生成新的摘要（整合历史摘要）
        new_summary = generate_summary(
            messages=messages_to_compress,
            previous_summary=current_summary
        )
        
        log.info(f"[Memory] Generated new summary: {new_summary[:100]}...")
        
        # 更新数据库
        update_summary(
            session_id=session_id,
            summary=new_summary,
            index=compress_end_index
        )
        
        log.info(f"[Memory] Updated index to: {compress_end_index}")
        
        # 5. 返回优化后的消息
        optimized_messages = _build_optimized_messages(new_summary, messages, compress_end_index)
        log.info(f"[Memory] Returning {len(optimized_messages)} optimized messages")
        
        return optimized_messages
        
    except Exception as e:
        log.error(f"[Memory] Error in message_memory_optimize: {str(e)}")
        log.error(f"[Memory] Falling back to original messages")
        # 发生错误时返回原始消息，确保系统继续运行
        return messages


def _build_optimized_messages(
    summary: str, 
    full_messages: List[Dict[str, Any]], 
    index: int
) -> List[Dict[str, Any]]:
    """
    构建优化后的消息列表
    
    Args:
        summary: 压缩后的历史摘要
        full_messages: 完整的消息列表
        index: 已压缩的消息索引
        
    Returns:
        优化后的消息列表
    """
    # 获取未压缩的消息
    recent_messages = full_messages[index:]
    
    if summary and len(summary.strip()) > 0 and len(recent_messages) > 0:
        # 有摘要且有未压缩消息，将 summary 作为上下文信息添加到第一条消息前
        # 注意：不能使用 role="system"，因为 create_agent 已经有 instructions 了
        # 将 summary 作为一条独立的 user 消息添加在开头
        summary_context = {
            "role": "user",
            "content": f"[Context from previous conversation]: {summary}"
        }
        return [summary_context] + recent_messages
    else:
        # 无摘要或无消息，直接返回未压缩的消息
        return recent_messages


def get_optimized_messages(session_id: str) -> List[Dict[str, Any]]:
    """
    获取优化后的消息列表（不触发新的压缩）
    
    Args:
        session_id: 会话ID
        
    Returns:
        优化后的消息列表
    """
    try:
        record = get_session_message(session_id)
        
        if record is None:
            return []
        
        return _build_optimized_messages(
            summary=record['summary'],
            full_messages=record['messages'],
            index=record['index']
        )
        
    except Exception as e:
        log.error(f"[Memory] Error in get_optimized_messages: {str(e)}")
        return []


def get_compression_stats(session_id: str) -> Dict[str, Any]:
    """
    获取压缩统计信息
    
    Args:
        session_id: 会话ID
        
    Returns:
        压缩统计信息字典
    """
    try:
        record = get_session_message(session_id)
        
        if record is None:
            return {
                "exists": False,
                "total_messages": 0,
                "compressed_messages": 0,
                "uncompressed_messages": 0,
                "has_summary": False,
                "summary_length": 0
            }
        
        total = len(record['messages'])
        compressed = record['index']
        uncompressed = total - compressed
        
        return {
            "exists": True,
            "total_messages": total,
            "compressed_messages": compressed,
            "uncompressed_messages": uncompressed,
            "has_summary": bool(record['summary']),
            "summary_length": len(record['summary']) if record['summary'] else 0,
            "compression_ratio": f"{compressed}/{total}" if total > 0 else "0/0"
        }
        
    except Exception as e:
        log.error(f"[Memory] Error in get_compression_stats: {str(e)}")
        return {"error": str(e)}


# 测试函数
def test_message_memory():
    """测试消息内存管理"""
    test_session_id = "test_session_123"
    
    # 模拟对话
    messages = []
    for i in range(15):
        messages.append({"role": "user", "content": f"User message {i+1}"})
        messages.append({"role": "assistant", "content": f"Assistant response {i+1}"})
    
    print(f"Total messages: {len(messages)}")
    
    # 第一次优化
    optimized = message_memory_optimize(test_session_id, messages)
    print(f"Optimized messages count: {len(optimized)}")
    
    # 获取统计信息
    stats = get_compression_stats(test_session_id)
    print(f"Compression stats: {stats}")
    
    # 打印优化后的消息
    for msg in optimized[:3]:
        print(f"{msg['role']}: {msg['content'][:50]}...")


if __name__ == "__main__":
    test_message_memory()

