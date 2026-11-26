"""Замер памяти на чистом Python (без Kivy) — для README и контроля.

    python tools/memory_report.py

Сравнивает два режима:
* загрузить все уроки сразу (так делать нельзя);
* листать уроки с кэшем на 1 тему (так работает приложение).
"""
from __future__ import annotations

import gc
import sys
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.content import ContentRepository  # noqa: E402


def kilobytes(value: int) -> str:
    return f"{value / 1024:.1f} КиБ"


def run_loaded_all() -> tuple[int, int]:
    repo = ContentRepository(cache_limit=99)
    gc.collect()
    tracemalloc.start()
    before = tracemalloc.get_traced_memory()[0]
    lessons = [repo.get(topic.id) for topic in repo.topics]
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert len(lessons) == len(repo.topics)
    return current - before, peak - before


def run_lazy() -> tuple[int, int, int]:
    repo = ContentRepository(cache_limit=1)
    gc.collect()
    tracemalloc.start()
    before = tracemalloc.get_traced_memory()[0]
    for topic in repo.topics:
        repo.get(topic.id)
    current, peak = tracemalloc.get_traced_memory()
    cache = repo.cache_size
    tracemalloc.stop()
    return current - before, peak - before, cache


def main() -> int:
    all_current, all_peak = run_loaded_all()
    lazy_current, lazy_peak, cache = run_lazy()
    print("Все 11 уроков сразу:")
    print("  занято:", kilobytes(all_current), " пик:", kilobytes(all_peak))
    print("Ленивый режим (кэш 1):")
    print("  занято:", kilobytes(lazy_current), " пик:", kilobytes(lazy_peak))
    print("  в кэше после обхода:", cache, "урок")
    print(
        "Экономия по текущему python-хипу:",
        kilobytes(max(0, all_current - lazy_current)),
        f"({100 * (1 - lazy_current / max(1, all_current)):.0f} % меньше)",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
