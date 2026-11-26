"""Прогресс ученика в SQLite.

Никаких списков попыток в оперативной памяти: наружу отдаются только
маленькие словари/кортежи, а всё остальное лежит на диске. Настройки SQLite
(маленький кэш, WAL, временные файлы на диске) снижают расход RAM и не
блокируют приложение на телефоне.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from .config import PASS_PERCENT

_SCHEMA = """
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id TEXT NOT NULL,
    correct INTEGER NOT NULL,
    total INTEGER NOT NULL,
    percent INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attempts_lesson ON attempts(lesson_id);

CREATE TABLE IF NOT EXISTS lesson_progress (
    lesson_id TEXT PRIMARY KEY,
    best_percent INTEGER NOT NULL DEFAULT 0,
    best_correct INTEGER NOT NULL DEFAULT 0,
    best_total INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL
);
"""


class StorageError(RuntimeError):
    """Хранилище закрыто или недоступно."""


class ProgressStore:
    __slots__ = ("_conn", "_path")

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        if self._path != ":memory:":
            Path(self._path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = sqlite3.connect(
            self._path, timeout=5.0
        )
        self._conn.row_factory = sqlite3.Row
        self._configure()
        with self._conn:
            self._conn.executescript(_SCHEMA)

    # -------------------------------------------------------------- lifecycle
    def _configure(self) -> None:
        conn = self._require_conn()
        cursor = conn.cursor()
        try:
            if self._path != ":memory:":
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA temp_store=FILE")
                cursor.execute("PRAGMA mmap_size=0")
            # 256 КиБ страничного кэша вместо ~2 МиБ по умолчанию.
            cursor.execute("PRAGMA cache_size=-256")
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    def _require_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise StorageError("хранилище уже закрыто")
        return self._conn

    def close(self) -> None:
        if self._conn is None:
            return
        try:
            if self._path != ":memory:":
                self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            pass
        try:
            self._conn.close()
        finally:
            self._conn = None

    @property
    def closed(self) -> bool:
        return self._conn is None

    # ---------------------------------------------------------------- queries
    def best_percent(self, lesson_id: str) -> int:
        row = self._require_conn().execute(
            "SELECT best_percent FROM lesson_progress WHERE lesson_id = ?",
            (lesson_id,),
        ).fetchone()
        return int(row[0]) if row is not None else 0

    def progress_map(self) -> dict[str, int]:
        rows = self._require_conn().execute(
            "SELECT lesson_id, best_percent FROM lesson_progress WHERE best_percent > 0"
        ).fetchall()
        return {str(row[0]): int(row[1]) for row in rows}

    def attempts_count(self, lesson_id: str | None = None) -> int:
        conn = self._require_conn()
        if lesson_id is None:
            row = conn.execute("SELECT COUNT(*) FROM attempts").fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) FROM attempts WHERE lesson_id = ?", (lesson_id,)
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def overall(self) -> tuple[int, int, int]:
        """(пройдено тем, тем с попытками, средний лучший процент)."""
        values = list(self.progress_map().values())
        completed = sum(1 for value in values if value >= PASS_PERCENT)
        attempted = len(values)
        average = int(round(sum(values) / len(values))) if values else 0
        return completed, attempted, average

    # ----------------------------------------------------------------- record
    def save_attempt(self, lesson_id: str, correct: int, total: int) -> tuple[int, bool]:
        """Сохраняет попытку. Возвращает (процент, новый ли это рекорд)."""
        if not isinstance(lesson_id, str) or not lesson_id:
            raise ValueError("lesson_id должен быть непустой строкой")
        if total <= 0:
            raise ValueError("total должен быть положительным")
        if correct < 0 or correct > total:
            raise ValueError("correct должен быть в диапазоне 0..total")

        percent = int((correct * 100 + total // 2) // total)
        now = int(time.time())
        conn = self._require_conn()
        with conn:
            row = conn.execute(
                "SELECT best_percent, best_correct, best_total FROM lesson_progress "
                "WHERE lesson_id = ?",
                (lesson_id,),
            ).fetchone()
            previous = int(row[0]) if row is not None else 0
            is_record = percent > previous
            if row is None:
                conn.execute(
                    "INSERT INTO lesson_progress "
                    "(lesson_id, best_percent, best_correct, best_total, attempts, updated_at) "
                    "VALUES (?, ?, ?, ?, 1, ?)",
                    (lesson_id, percent, correct, total, now),
                )
            else:
                best_percent = max(previous, percent)
                best_correct = correct if is_record else int(row[1])
                best_total = total if is_record else int(row[2])
                conn.execute(
                    "UPDATE lesson_progress SET best_percent = ?, best_correct = ?, "
                    "best_total = ?, attempts = attempts + 1, updated_at = ? "
                    "WHERE lesson_id = ?",
                    (best_percent, best_correct, best_total, now, lesson_id),
                )
            conn.execute(
                "INSERT INTO attempts (lesson_id, correct, total, percent, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (lesson_id, correct, total, percent, now),
            )
        return percent, is_record

    def reset(self) -> None:
        conn = self._require_conn()
        with conn:
            conn.execute("DELETE FROM attempts")
            conn.execute("DELETE FROM lesson_progress")
        if self._path != ":memory:":
            try:
                conn.execute("VACUUM")
            except sqlite3.Error:
                pass

    def recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """Последние попытки — пригодится для отладки и экрана статистики."""
        if limit <= 0:
            return []
        rows = self._require_conn().execute(
            "SELECT lesson_id, correct, total, percent, created_at "
            "FROM attempts ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "lesson_id": str(row["lesson_id"]),
                "correct": int(row["correct"]),
                "total": int(row["total"]),
                "percent": int(row["percent"]),
                "created_at": int(row["created_at"]),
            }
            for row in rows
        ]
