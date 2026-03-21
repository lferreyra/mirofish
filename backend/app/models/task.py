"""
Task status management.
Tracks long-running tasks (graph building, report generation, etc.)
Persisted to SQLite for crash resilience.
"""

import json
import uuid
import threading
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    task_id: str
    task_type: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    progress: int = 0
    message: str = ""
    result: Optional[Dict] = None
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    progress_detail: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "progress": self.progress,
            "message": self.message,
            "progress_detail": self.progress_detail,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


def _json_dumps(obj) -> Optional[str]:
    """Serialize dict/list to JSON string, or None."""
    if obj is None:
        return None
    return json.dumps(obj, ensure_ascii=False)


def _json_loads(s) -> Optional[Dict]:
    """Deserialize JSON string to dict/list, or None."""
    if s is None:
        return None
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None


def _row_to_task(row) -> Task:
    """Convert a sqlite3.Row to a Task dataclass."""
    return Task(
        task_id=row['task_id'],
        task_type=row['task_type'],
        status=TaskStatus(row['status']),
        created_at=datetime.fromisoformat(row['created_at']),
        updated_at=datetime.fromisoformat(row['updated_at']),
        progress=row['progress'] or 0,
        message=row['message'] or '',
        result=_json_loads(row['result']),
        error=row['error'],
        metadata=_json_loads(row['metadata']) or {},
        progress_detail=_json_loads(row['progress_detail']) or {},
    )


class TaskManager:
    """
    Task manager backed by SQLite.
    Thread-safe singleton.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._write_lock = threading.Lock()
        return cls._instance

    def _get_db(self):
        from ..database import get_db
        return get_db()

    def create_task(self, task_type: str, metadata: Optional[Dict] = None) -> str:
        task_id = str(uuid.uuid4())
        now = datetime.now()

        db = self._get_db()
        db.execute(
            """INSERT INTO tasks
            (task_id, task_type, status, created_at, updated_at,
             progress, message, result, error, metadata, progress_detail)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task_id, task_type, TaskStatus.PENDING.value,
                now.isoformat(), now.isoformat(),
                0, '', None, None,
                _json_dumps(metadata or {}),
                _json_dumps({}),
            )
        )
        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        db = self._get_db()
        row = db.fetchone("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        if row is None:
            return None
        return _row_to_task(row)

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        progress_detail: Optional[Dict] = None
    ):
        sets = ["updated_at = ?"]
        params = [datetime.now().isoformat()]

        if status is not None:
            sets.append("status = ?")
            params.append(status.value)
        if progress is not None:
            sets.append("progress = ?")
            params.append(progress)
        if message is not None:
            sets.append("message = ?")
            params.append(message)
        if result is not None:
            sets.append("result = ?")
            params.append(_json_dumps(result))
        if error is not None:
            sets.append("error = ?")
            params.append(error)
        if progress_detail is not None:
            sets.append("progress_detail = ?")
            params.append(_json_dumps(progress_detail))

        params.append(task_id)

        db = self._get_db()
        db.execute(
            f"UPDATE tasks SET {', '.join(sets)} WHERE task_id = ?",
            tuple(params)
        )

    def complete_task(self, task_id: str, result: Dict):
        self.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            message="Task completed",
            result=result
        )

    def fail_task(self, task_id: str, error: str):
        self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            message="Task failed",
            error=error
        )

    def list_tasks(self, task_type: Optional[str] = None) -> list:
        db = self._get_db()
        if task_type:
            rows = db.fetchall(
                "SELECT * FROM tasks WHERE task_type = ? ORDER BY created_at DESC",
                (task_type,)
            )
        else:
            rows = db.fetchall("SELECT * FROM tasks ORDER BY created_at DESC")
        return [_row_to_task(row).to_dict() for row in rows]

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        cutoff = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
        db = self._get_db()
        db.execute(
            "DELETE FROM tasks WHERE created_at < ? AND status IN (?, ?)",
            (cutoff, TaskStatus.COMPLETED.value, TaskStatus.FAILED.value)
        )
