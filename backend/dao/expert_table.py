import os
import json
from typing import Dict, Any, Optional, List
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# 创建数据库基类
Base = declarative_base()

# 定义workflow_version表模型
class RewriteExpert(Base):
    __tablename__ = 'rewrite_expert'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)  # 描述
    content = Column(Text, nullable=True)  # 内容
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        def _parse_json_or_raw(value: Optional[str]) -> Any:
            if value is None:
                return None
            try:
                return json.loads(value)
            except Exception:
                return value

        def _format_dt(dt: Optional[datetime]) -> Optional[str]:
            if dt is None:
                return None
            # 存储为UTC时间，序列化为ISO字符串并加Z
            try:
                return dt.isoformat() + 'Z'
            except Exception:
                return str(dt)

        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'content': self.content,
            'createTime': _format_dt(self.create_time),
            'updateTime': _format_dt(self.update_time),
        }

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # 默认数据库路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_dir = os.path.join(current_dir, '..', 'data')
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, 'rewrite_expert.db')
        
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # 创建表
        Base.metadata.create_all(bind=self.engine)
        # 轻量级表结构升级（为已有库添加新列）
        self._ensure_schema()
        # 首次初始化时从内置JSON写入默认数据
        self._seed_initial_data()
        
    def get_session(self):
        """获取数据库会话"""
        return self.SessionLocal()
    
    def save_rewrite_expert(self, name: str, description: str, content: str) -> int:
        """新增一条专家记录，返回新ID"""
        session = self.get_session()
        try:
            rewrite_expert = RewriteExpert(
                name=name,
                description=self._serialize_field(description),
                content=self._string_field(content)
            )
            session.add(rewrite_expert)
            session.commit()
            session.refresh(rewrite_expert)
            return rewrite_expert.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def _ensure_schema(self) -> None:
        """确保SQLite中存在新列（非破坏性升级）。"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(rewrite_expert)"))
                existing_columns = {row[1] for row in result}
                if 'create_time' not in existing_columns:
                    conn.execute(text("ALTER TABLE rewrite_expert ADD COLUMN create_time TEXT"))
                    conn.execute(text("UPDATE rewrite_expert SET create_time = COALESCE(create_time, CURRENT_TIMESTAMP)"))
                if 'update_time' not in existing_columns:
                    conn.execute(text("ALTER TABLE rewrite_expert ADD COLUMN update_time TEXT"))
                    conn.execute(text("UPDATE rewrite_expert SET update_time = COALESCE(update_time, CURRENT_TIMESTAMP)"))
        except Exception:
            # 忽略升级失败，后续写入由ORM默认值补齐
            pass

    def _seed_initial_data(self) -> None:
        """如果表为空，则从 data/workflow_rewrite_expert.json 导入初始数据。"""
        try:
            # 仅当表为空时导入
            session = self.get_session()
            try:
                has_any = session.query(RewriteExpert.id).first() is not None
            finally:
                session.close()
            if has_any:
                return

            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, '..', 'data', 'workflow_rewrite_expert.json')
            json_path = os.path.abspath(json_path)
            if not os.path.exists(json_path):
                return

            with open(json_path, 'r', encoding='utf-8') as f:
                items = json.load(f)
                if not isinstance(items, list):
                    return

            session = self.get_session()
            try:
                for entry in items:
                    name = entry.get('name')
                    if not name:
                        continue
                    description = entry.get('description')
                    content = entry.get('content')
                    expert = RewriteExpert(
                        name=name,
                        description=description,
                        content=content
                    )
                    session.add(expert)
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        except Exception:
            # 读取或导入失败不影响正常启动
            pass
    
    def get_rewrite_expert_by_id(self, expert_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取专家记录"""
        session = self.get_session()
        try:
            expert = session.query(RewriteExpert).filter(RewriteExpert.id == expert_id).first()
            return expert.to_dict() if expert else None
        finally:
            session.close()

    def list_rewrite_experts(self) -> List[Dict[str, Any]]:
        """获取所有专家记录，按ID倒序"""
        session = self.get_session()
        try:
            experts = session.query(RewriteExpert).order_by(RewriteExpert.id.asc()).all()
            return [e.to_dict() for e in experts]
        finally:
            session.close()
    
    def list_rewrite_experts_short(self) -> List[Dict[str, Any]]:
        """获取所有专家记录，按ID倒序"""
        session = self.get_session()
        try:
            experts = session.query(RewriteExpert).order_by(RewriteExpert.id.asc()).all()
            return [{"name": e.name, "description": e.description} for e in experts]
        finally:
            session.close()
    
    def get_rewrite_expert_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取专家记录"""
        session = self.get_session()
        try:
            expert = session.query(RewriteExpert).filter(RewriteExpert.name == name).first()
            return expert.to_dict() if expert else None
        finally:
            session.close()
    
    def get_rewrite_expert_by_name_list(self, name_list: List[str]) -> List[Dict[str, Any]]:
        """根据名称列表获取专家记录"""
        session = self.get_session()
        try:
            experts = session.query(RewriteExpert).filter(RewriteExpert.name.in_(name_list)).all()
            return [e.to_dict() for e in experts]
        finally:
            session.close()

    def update_rewrite_expert(self, expert_id: int, name: Optional[str] = None, description: Optional[Any] = None, content: Optional[Any] = None) -> bool:
        """根据ID更新专家记录的部分或全部字段"""
        session = self.get_session()
        try:
            expert = session.query(RewriteExpert).filter(RewriteExpert.id == expert_id).first()
            if not expert:
                return False

            if name is not None:
                expert.name = name
            if description is not None:
                expert.description = self._serialize_field(description)
            if content is not None:
                expert.content = self._string_field(content)

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def delete_rewrite_expert(self, expert_id: int) -> bool:
        """根据ID删除专家记录"""
        session = self.get_session()
        try:
            expert = session.query(RewriteExpert).filter(RewriteExpert.id == expert_id).first()
            if not expert:
                return False
            session.delete(expert)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def _serialize_field(value: Optional[Any]) -> Optional[str]:
        """将任意入参序列化为可存储的字符串。None -> None，其他 -> str/JSON"""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)

    @staticmethod
    def _string_field(value: Optional[Any]) -> Optional[str]:
        """确保字段以字符串形式存储（不做JSON序列化）。"""
        if value is None:
            return None
        return value if isinstance(value, str) else str(value)

# 全局数据库管理器实例
db_manager = DatabaseManager()

# 便捷函数（对外导出）
def create_rewrite_expert(name: str, description: Any = None, content: Any = None) -> int:
    return db_manager.save_rewrite_expert(name=name, description=description, content=content)

def get_rewrite_expert(expert_id: int) -> Optional[Dict[str, Any]]:
    return db_manager.get_rewrite_expert_by_id(expert_id)

def list_rewrite_experts() -> List[Dict[str, Any]]:
    return db_manager.list_rewrite_experts()

def update_rewrite_expert_by_id(expert_id: int, name: Optional[str] = None, description: Optional[Any] = None, content: Optional[Any] = None) -> bool:
    return db_manager.update_rewrite_expert(expert_id=expert_id, name=name, description=description, content=content)

def delete_rewrite_expert_by_id(expert_id: int) -> bool:
    return db_manager.delete_rewrite_expert(expert_id)

def list_rewrite_experts_short() -> List[Dict[str, Any]]:
    return db_manager.list_rewrite_experts_short()

def get_rewrite_expert_by_name(name: str) -> Optional[Dict[str, Any]]:
    return db_manager.get_rewrite_expert_by_name(name)

def get_rewrite_expert_by_name_list(name_list: List[str]) -> List[Dict[str, Any]]:
    return db_manager.get_rewrite_expert_by_name_list(name_list)