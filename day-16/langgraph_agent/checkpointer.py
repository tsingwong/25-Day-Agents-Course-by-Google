"""
Checkpointer 模块 - 状态持久化

生产级别的状态持久化实现，支持:
- 内存存储（默认，快速测试）
- SQLite 本地持久化（需要安装 langgraph-checkpoint-sqlite）
- 可扩展到 PostgreSQL/Redis（生产环境）

核心功能:
- 保存和恢复 Agent 执行状态
- 支持断点续跑
- 支持 time-travel debugging

安装 SQLite 支持:
    uv pip install langgraph-checkpoint-sqlite
"""

import os
import json
import sqlite3
import logging
from typing import Optional, Any, Dict
from datetime import datetime
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from enum import Enum

# LangGraph 的 checkpointer
from langgraph.checkpoint.memory import MemorySaver

# SQLite Saver 是可选的，需要单独安装
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False
    SqliteSaver = None

logger = logging.getLogger(__name__)


class CheckpointerType(Enum):
    """Checkpointer 类型"""
    MEMORY = "memory"
    SQLITE = "sqlite"


@dataclass
class TaskMetadata:
    """任务元数据 - 用于追踪任务状态"""
    task_id: str
    thread_id: str
    created_at: str
    updated_at: str
    status: str  # pending, waiting_approval, approved, rejected, completed, failed
    current_node: Optional[str] = None
    pending_action: Optional[str] = None
    user_input: Optional[str] = None
    error_message: Optional[str] = None


class TaskStore:
    """
    任务存储 - 管理 Human-in-the-Loop 任务状态

    与 LangGraph Checkpointer 配合使用:
    - Checkpointer: 保存图执行状态
    - TaskStore: 保存业务元数据（审批状态、用户输入等）
    """

    def __init__(self, db_path: str = "data/tasks.db"):
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logger.info(f"Created database directory: {db_dir}")

    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_node TEXT,
                    pending_action TEXT,
                    user_input TEXT,
                    error_message TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status
                ON tasks(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_thread
                ON tasks(thread_id)
            """)
            conn.commit()
            logger.info("Task store initialized")

    @contextmanager
    def _get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_task(self, task_id: str, thread_id: str, user_input: str) -> TaskMetadata:
        """创建新任务"""
        now = datetime.utcnow().isoformat()
        task = TaskMetadata(
            task_id=task_id,
            thread_id=thread_id,
            created_at=now,
            updated_at=now,
            status="pending",
            user_input=user_input,
        )

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO tasks
                (task_id, thread_id, created_at, updated_at, status,
                 current_node, pending_action, user_input, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id, task.thread_id, task.created_at, task.updated_at,
                task.status, task.current_node, task.pending_action,
                task.user_input, task.error_message
            ))
            conn.commit()

        logger.info(f"Created task: {task_id}")
        return task

    def get_task(self, task_id: str) -> Optional[TaskMetadata]:
        """获取任务"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()

            if row:
                return TaskMetadata(**dict(row))
            return None

    def update_task(self, task_id: str, **updates) -> Optional[TaskMetadata]:
        """更新任务"""
        updates["updated_at"] = datetime.utcnow().isoformat()

        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [task_id]

        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE tasks SET {set_clause} WHERE task_id = ?",
                values
            )
            conn.commit()

        logger.info(f"Updated task {task_id}: {updates}")
        return self.get_task(task_id)

    def get_pending_approvals(self) -> list[TaskMetadata]:
        """获取所有等待审批的任务"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status = 'waiting_approval' ORDER BY created_at"
            ).fetchall()
            return [TaskMetadata(**dict(row)) for row in rows]

    def get_tasks_by_status(self, status: str) -> list[TaskMetadata]:
        """按状态获取任务列表"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC",
                (status,)
            ).fetchall()
            return [TaskMetadata(**dict(row)) for row in rows]


def create_checkpointer(
    checkpointer_type: CheckpointerType = CheckpointerType.MEMORY,
    db_path: str = "data/checkpoints.db"
) -> Any:
    """
    创建 Checkpointer 实例

    Args:
        checkpointer_type: 存储类型（默认 MEMORY）
        db_path: SQLite 数据库路径（仅 SQLITE 类型需要）

    Returns:
        LangGraph Checkpointer 实例

    注意:
        SQLite 需要安装: uv pip install langgraph-checkpoint-sqlite
    """
    if checkpointer_type == CheckpointerType.MEMORY:
        logger.info("Using MemorySaver (data will be lost on restart)")
        return MemorySaver()

    elif checkpointer_type == CheckpointerType.SQLITE:
        if not SQLITE_AVAILABLE:
            logger.warning(
                "SQLite checkpointer not available. "
                "Install with: uv pip install langgraph-checkpoint-sqlite. "
                "Falling back to MemorySaver."
            )
            return MemorySaver()

        # 确保目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        logger.info(f"Using SqliteSaver with database: {db_path}")
        # 创建连接
        conn = sqlite3.connect(db_path, check_same_thread=False)
        return SqliteSaver(conn)

    else:
        raise ValueError(f"Unknown checkpointer type: {checkpointer_type}")


# 全局单例
_task_store: Optional[TaskStore] = None
_checkpointer: Optional[Any] = None


def get_task_store(db_path: str = "data/tasks.db") -> TaskStore:
    """获取 TaskStore 单例"""
    global _task_store
    if _task_store is None:
        _task_store = TaskStore(db_path)
    return _task_store


def get_checkpointer(
    checkpointer_type: CheckpointerType = CheckpointerType.SQLITE,
    db_path: str = "data/checkpoints.db"
) -> Any:
    """获取 Checkpointer 单例"""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = create_checkpointer(checkpointer_type, db_path)
    return _checkpointer
