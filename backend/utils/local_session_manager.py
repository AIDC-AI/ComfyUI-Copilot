# Copyright (C) 2025 AIDC-AI
# Licensed under the MIT License.

"""
Local session management without external server dependency.
Provides UUID-based session tracking with SQLite storage.
"""

import os
import sqlite3
import time
import uuid
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from threading import Lock
from pathlib import Path
import json

from .logger import log


@dataclass
class LocalSession:
    """Local session data structure"""
    session_id: str
    created_at: float
    last_activity: float
    workflow_checkpoints: List[int]
    config: Dict[str, Any]


class LocalSessionManager:
    """
    Manages user sessions locally without external server.
    Uses SQLite for persistence and thread-safe operations.
    """
    
    def __init__(self, db_path: str = "./data/sessions.db"):
        self.db_path = db_path
        self._lock = Lock()
        self._ensure_db_directory()
        self._init_database()
    
    def _ensure_db_directory(self):
        """Ensure the database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            log.info(f"Created session database directory: {db_dir}")
    
    def _init_database(self):
        """Initialize the SQLite database with required tables"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        created_at REAL NOT NULL,
                        last_activity REAL NOT NULL,
                        workflow_checkpoints TEXT DEFAULT '[]',
                        config TEXT DEFAULT '{}'
                    )
                """)
                conn.commit()
                log.info("Local session database initialized")
            finally:
                conn.close()
    
    def create_session(self, config: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session with a unique UUID.
        
        Args:
            config: Optional configuration dict for the session
            
        Returns:
            session_id: UUID string for the new session
        """
        session_id = str(uuid.uuid4())
        current_time = time.time()
        
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sessions (session_id, created_at, last_activity, workflow_checkpoints, config)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    session_id,
                    current_time,
                    current_time,
                    json.dumps([]),
                    json.dumps(config or {})
                ))
                conn.commit()
                log.info(f"Created new local session: {session_id}")
            finally:
                conn.close()
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[LocalSession]:
        """
        Retrieve a session by ID.
        
        Args:
            session_id: Session UUID
            
        Returns:
            LocalSession object or None if not found
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT session_id, created_at, last_activity, workflow_checkpoints, config
                    FROM sessions
                    WHERE session_id = ?
                """, (session_id,))
                
                row = cursor.fetchone()
                if row:
                    return LocalSession(
                        session_id=row[0],
                        created_at=row[1],
                        last_activity=row[2],
                        workflow_checkpoints=json.loads(row[3]),
                        config=json.loads(row[4])
                    )
                return None
            finally:
                conn.close()
    
    def update_session_activity(self, session_id: str) -> None:
        """
        Update the last activity timestamp for a session.
        
        Args:
            session_id: Session UUID
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sessions
                    SET last_activity = ?
                    WHERE session_id = ?
                """, (time.time(), session_id))
                conn.commit()
            finally:
                conn.close()
    
    def store_workflow_checkpoint(self, session_id: str, checkpoint_id: int) -> None:
        """
        Associate a workflow checkpoint with a session.
        
        Args:
            session_id: Session UUID
            checkpoint_id: Workflow checkpoint ID
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # Get current checkpoints
                cursor.execute("""
                    SELECT workflow_checkpoints FROM sessions WHERE session_id = ?
                """, (session_id,))
                row = cursor.fetchone()
                
                if row:
                    checkpoints = json.loads(row[0])
                    checkpoints.append(checkpoint_id)
                    
                    # Update with new checkpoint
                    cursor.execute("""
                        UPDATE sessions
                        SET workflow_checkpoints = ?, last_activity = ?
                        WHERE session_id = ?
                    """, (json.dumps(checkpoints), time.time(), session_id))
                    conn.commit()
                    log.info(f"Stored checkpoint {checkpoint_id} for session {session_id}")
            finally:
                conn.close()
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """
        Remove sessions older than max_age_hours.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
            
        Returns:
            Number of sessions deleted
        """
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM sessions
                    WHERE last_activity < ?
                """, (cutoff_time,))
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    log.info(f"Cleaned up {deleted_count} expired sessions")
                
                return deleted_count
            finally:
                conn.close()
    
    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_id: Session UUID
            
        Returns:
            True if session exists, False otherwise
        """
        return self.get_session(session_id) is not None
    
    def get_or_create_session(self, session_id: Optional[str] = None, 
                             config: Optional[Dict[str, Any]] = None) -> str:
        """
        Get an existing session or create a new one.
        
        Args:
            session_id: Optional existing session ID
            config: Optional configuration for new session
            
        Returns:
            session_id: Existing or new session UUID
        """
        if session_id and self.session_exists(session_id):
            self.update_session_activity(session_id)
            return session_id
        else:
            return self.create_session(config)


# Global instance
_session_manager: Optional[LocalSessionManager] = None
_manager_lock = Lock()


def get_session_manager() -> LocalSessionManager:
    """Get the global session manager instance"""
    global _session_manager
    
    with _manager_lock:
        if _session_manager is None:
            # Get database path from environment or use default
            db_path = os.getenv("SESSION_DB_PATH", "./data/sessions.db")
            _session_manager = LocalSessionManager(db_path)
        
        return _session_manager
