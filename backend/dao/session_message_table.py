'''
Author: ai-business-hql ai.bussiness.hql@gmail.com
Date: 2025-11-19
LastEditors: ai-business-hql ai.bussiness.hql@gmail.com
LastEditTime: 2025-11-19
FilePath: /ComfyUI-Copilot/backend/dao/session_message_table.py
Description: Session message table for conversation memory management with compression
'''

import os
import json
from typing import Dict, Any, Optional, List
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# 创建数据库基类
Base = declarative_base()

# 定义session_message表模型
class SessionMessage(Base):
    __tablename__ = 'session_message'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, unique=True)  # 每个session只有一条记录
    messages = Column(Text, nullable=False)  # JSON字符串，存储完整消息列表
    index = Column(Integer, default=0)  # 已压缩的消息数量，messages[:index]已被摘要
    summary = Column(Text, nullable=True)  # 压缩后的历史摘要
    attributes = Column(Text, nullable=True)  # JSON字符串，存储额外属性
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'messages': json.loads(self.messages) if self.messages else [],
            'index': self.index,
            'summary': self.summary,
            'attributes': json.loads(self.attributes) if self.attributes else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SessionMessageManager:
    """会话消息管理器"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # 默认数据库路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_dir = os.path.join(current_dir, '..', 'data')
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, 'session_message.db')
        
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # 创建表
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self):
        """获取数据库会话"""
        return self.SessionLocal()
    
    def get_session_message(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取指定session的消息记录"""
        session = self.get_session()
        try:
            record = session.query(SessionMessage)\
                .filter(SessionMessage.session_id == session_id)\
                .first()
            
            if record:
                return record.to_dict()
            return None
        finally:
            session.close()
    
    def save_session_message(
        self, 
        session_id: str, 
        messages: List[Dict[str, Any]], 
        index: int = 0,
        summary: str = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> int:
        """保存或更新会话消息记录"""
        session = self.get_session()
        try:
            # 查找是否已存在
            record = session.query(SessionMessage)\
                .filter(SessionMessage.session_id == session_id)\
                .first()
            
            if record:
                # 更新已有记录
                record.messages = json.dumps(messages, ensure_ascii=False)
                record.index = index
                record.summary = summary
                if attributes:
                    record.attributes = json.dumps(attributes, ensure_ascii=False)
                session.commit()
                session.refresh(record)
                return record.id
            else:
                # 创建新记录
                new_record = SessionMessage(
                    session_id=session_id,
                    messages=json.dumps(messages, ensure_ascii=False),
                    index=index,
                    summary=summary,
                    attributes=json.dumps(attributes, ensure_ascii=False) if attributes else None
                )
                session.add(new_record)
                session.commit()
                session.refresh(new_record)
                return new_record.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def update_summary(self, session_id: str, summary: str, index: int) -> bool:
        """更新指定session的摘要和索引"""
        session = self.get_session()
        try:
            record = session.query(SessionMessage)\
                .filter(SessionMessage.session_id == session_id)\
                .first()
            
            if record:
                record.summary = summary
                record.index = index
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_session_message(self, session_id: str) -> bool:
        """删除指定session的消息记录"""
        session = self.get_session()
        try:
            record = session.query(SessionMessage)\
                .filter(SessionMessage.session_id == session_id)\
                .first()
            
            if record:
                session.delete(record)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

# 全局会话消息管理器实例
session_message_manager = SessionMessageManager()

def get_session_message(session_id: str) -> Optional[Dict[str, Any]]:
    """获取会话消息的便捷函数"""
    return session_message_manager.get_session_message(session_id)

def save_session_message(
    session_id: str, 
    messages: List[Dict[str, Any]], 
    index: int = 0,
    summary: str = None,
    attributes: Optional[Dict[str, Any]] = None
) -> int:
    """保存会话消息的便捷函数"""
    return session_message_manager.save_session_message(
        session_id, messages, index, summary, attributes
    )

def update_summary(session_id: str, summary: str, index: int) -> bool:
    """更新摘要的便捷函数"""
    return session_message_manager.update_summary(session_id, summary, index)

def delete_session_message(session_id: str) -> bool:
    """删除会话消息的便捷函数"""
    return session_message_manager.delete_session_message(session_id)

