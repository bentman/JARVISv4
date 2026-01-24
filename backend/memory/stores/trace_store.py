"""
SQLite-backed Tier-2 episodic trace store (append-only).
"""
import json
import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, Optional


class TraceStore:
    """Append-only trace store for decisions, tool calls, and validations."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trace_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    decision_type TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trace_tool_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    tool_name TEXT,
                    params TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trace_validations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    validation_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def append_decision(self, task_id: str, decision_type: str, payload: Dict[str, Any]) -> None:
        timestamp = datetime.now(UTC).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO trace_decisions (task_id, timestamp, decision_type, payload) VALUES (?, ?, ?, ?)",
                (task_id, timestamp, decision_type, json.dumps(payload))
            )
            conn.commit()

    def append_tool_call(
        self,
        task_id: str,
        step_index: int,
        tool_name: Optional[str],
        params: Dict[str, Any],
        status: str,
        result: Optional[str],
        error: Optional[str]
    ) -> None:
        timestamp = datetime.now(UTC).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO trace_tool_calls (
                    task_id, step_index, timestamp, tool_name, params, status, result, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    step_index,
                    timestamp,
                    tool_name,
                    json.dumps(params),
                    status,
                    result,
                    error
                )
            )
            conn.commit()

    def append_validation(
        self,
        task_id: str,
        validation_type: str,
        status: str,
        details: Dict[str, Any]
    ) -> None:
        timestamp = datetime.now(UTC).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO trace_validations (task_id, timestamp, validation_type, status, details) VALUES (?, ?, ?, ?, ?)",
                (task_id, timestamp, validation_type, status, json.dumps(details))
            )
            conn.commit()