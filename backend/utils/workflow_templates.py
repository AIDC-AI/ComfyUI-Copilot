"""
Local Workflow Template System

Provides local workflow template storage, search, and generation capabilities
to replace external MCP workflow services.
"""

import json
import os
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from ..utils.logger import log


@dataclass
class WorkflowTemplate:
    """Represents a workflow template"""
    id: str                          # Unique template ID
    name: str                        # Template name
    description: str                 # Description of what the workflow does
    category: str                    # Category (text2image, img2img, controlnet, etc.)
    tags: List[str]                  # Search tags
    workflow_data: Dict[str, Any]    # ComfyUI workflow JSON (API format)
    workflow_data_ui: Optional[Dict[str, Any]] = None  # UI format (optional)
    author: str = "ComfyUI-Copilot"  # Template author
    version: str = "1.0"             # Template version
    required_models: List[str] = None  # List of required model files
    created_at: str = None           # Creation timestamp
    updated_at: str = None           # Last update timestamp
    usage_count: int = 0             # How many times this template was used
    rating: float = 0.0              # User rating (0-5)

    def __post_init__(self):
        if self.required_models is None:
            self.required_models = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowTemplate':
        """Create from dictionary"""
        return cls(**data)


class WorkflowTemplateManager:
    """Manages workflow templates stored in local SQLite database"""

    def __init__(self, db_path: str = None):
        """
        Initialize the template manager.

        Args:
            db_path: Path to SQLite database file (default: ./data/workflow_templates.db)
        """
        if db_path is None:
            data_dir = Path("./data")
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "workflow_templates.db")

        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize the database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags TEXT NOT NULL,  -- JSON array
                    workflow_data TEXT NOT NULL,  -- JSON
                    workflow_data_ui TEXT,  -- JSON (optional)
                    author TEXT DEFAULT 'ComfyUI-Copilot',
                    version TEXT DEFAULT '1.0',
                    required_models TEXT,  -- JSON array
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    usage_count INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0
                )
            """)

            # Create index for better search performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_category ON templates(category)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage ON templates(usage_count DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_rating ON templates(rating DESC)
            """)

            conn.commit()
            log.info(f"Workflow template database initialized at {self.db_path}")

    def add_template(self, template: WorkflowTemplate) -> bool:
        """
        Add a new template to the database.

        Args:
            template: WorkflowTemplate to add

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO templates (
                        id, name, description, category, tags,
                        workflow_data, workflow_data_ui, author, version,
                        required_models, created_at, updated_at, usage_count, rating
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    template.id,
                    template.name,
                    template.description,
                    template.category,
                    json.dumps(template.tags),
                    json.dumps(template.workflow_data),
                    json.dumps(template.workflow_data_ui) if template.workflow_data_ui else None,
                    template.author,
                    template.version,
                    json.dumps(template.required_models),
                    template.created_at,
                    template.updated_at,
                    template.usage_count,
                    template.rating
                ))
                conn.commit()
                log.info(f"Added template: {template.name} (ID: {template.id})")
                return True
        except Exception as e:
            log.error(f"Failed to add template {template.id}: {e}")
            return False

    def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """
        Get a template by ID.

        Args:
            template_id: Template ID

        Returns:
            WorkflowTemplate if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM templates WHERE id = ?",
                    (template_id,)
                )
                row = cursor.fetchone()

                if row:
                    return self._row_to_template(row)
                return None
        except Exception as e:
            log.error(f"Failed to get template {template_id}: {e}")
            return None

    def search_templates(
        self,
        query: str = "",
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
        sort_by: str = "usage_count"  # "usage_count", "rating", "created_at", "name"
    ) -> List[WorkflowTemplate]:
        """
        Search templates by query, category, and tags.

        Args:
            query: Search query (searches in name and description)
            category: Filter by category
            tags: Filter by tags (matches any)
            limit: Maximum number of results
            sort_by: Sort criterion

        Returns:
            List of matching WorkflowTemplates
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Build WHERE clause
                conditions = []
                params = []

                if query:
                    query_lower = query.lower()
                    conditions.append("(LOWER(name) LIKE ? OR LOWER(description) LIKE ?)")
                    params.extend([f"%{query_lower}%", f"%{query_lower}%"])

                if category:
                    conditions.append("category = ?")
                    params.append(category)

                if tags:
                    # Match any of the provided tags
                    tag_conditions = []
                    for tag in tags:
                        tag_conditions.append("tags LIKE ?")
                        params.append(f'%"{tag}"%')  # JSON array contains tag
                    conditions.append(f"({' OR '.join(tag_conditions)})")

                where_clause = " AND ".join(conditions) if conditions else "1=1"

                # Build ORDER BY clause
                sort_map = {
                    "usage_count": "usage_count DESC",
                    "rating": "rating DESC",
                    "created_at": "created_at DESC",
                    "name": "name ASC"
                }
                order_clause = sort_map.get(sort_by, "usage_count DESC")

                # Execute query
                query_sql = f"""
                    SELECT * FROM templates
                    WHERE {where_clause}
                    ORDER BY {order_clause}
                    LIMIT ?
                """
                params.append(limit)

                cursor = conn.execute(query_sql, params)
                rows = cursor.fetchall()

                return [self._row_to_template(row) for row in rows]

        except Exception as e:
            log.error(f"Failed to search templates: {e}")
            return []

    def increment_usage(self, template_id: str) -> bool:
        """
        Increment the usage count for a template.

        Args:
            template_id: Template ID

        Returns:
            True if successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE templates
                    SET usage_count = usage_count + 1,
                        updated_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), template_id))
                conn.commit()
                return True
        except Exception as e:
            log.error(f"Failed to increment usage for {template_id}: {e}")
            return False

    def update_rating(self, template_id: str, rating: float) -> bool:
        """
        Update the rating for a template.

        Args:
            template_id: Template ID
            rating: New rating (0-5)

        Returns:
            True if successful
        """
        try:
            rating = max(0.0, min(5.0, rating))  # Clamp to 0-5
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE templates
                    SET rating = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (rating, datetime.now().isoformat(), template_id))
                conn.commit()
                return True
        except Exception as e:
            log.error(f"Failed to update rating for {template_id}: {e}")
            return False

    def delete_template(self, template_id: str) -> bool:
        """
        Delete a template.

        Args:
            template_id: Template ID

        Returns:
            True if successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
                conn.commit()
                log.info(f"Deleted template: {template_id}")
                return True
        except Exception as e:
            log.error(f"Failed to delete template {template_id}: {e}")
            return False

    def get_all_categories(self) -> List[str]:
        """Get list of all unique categories"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT DISTINCT category FROM templates ORDER BY category")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            log.error(f"Failed to get categories: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get template database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                total_templates = conn.execute("SELECT COUNT(*) FROM templates").fetchone()[0]
                total_usage = conn.execute("SELECT SUM(usage_count) FROM templates").fetchone()[0] or 0
                avg_rating = conn.execute("SELECT AVG(rating) FROM templates WHERE rating > 0").fetchone()[0] or 0.0

                return {
                    "total_templates": total_templates,
                    "total_usage": total_usage,
                    "average_rating": round(avg_rating, 2),
                    "categories": self.get_all_categories()
                }
        except Exception as e:
            log.error(f"Failed to get statistics: {e}")
            return {}

    def _row_to_template(self, row: sqlite3.Row) -> WorkflowTemplate:
        """Convert database row to WorkflowTemplate"""
        return WorkflowTemplate(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            category=row["category"],
            tags=json.loads(row["tags"]),
            workflow_data=json.loads(row["workflow_data"]),
            workflow_data_ui=json.loads(row["workflow_data_ui"]) if row["workflow_data_ui"] else None,
            author=row["author"],
            version=row["version"],
            required_models=json.loads(row["required_models"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            usage_count=row["usage_count"],
            rating=row["rating"]
        )


# Global instance
_template_manager: Optional[WorkflowTemplateManager] = None


def get_template_manager() -> WorkflowTemplateManager:
    """Get or create the global template manager instance"""
    global _template_manager
    if _template_manager is None:
        _template_manager = WorkflowTemplateManager()
    return _template_manager
