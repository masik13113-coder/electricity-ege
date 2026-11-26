"""CLI-проверка контента: запускать после правки JSON.

    python tools/check_content.py

Проверяет схему, разметку, дубли id, количество вопросов и пересчитывает
все числовые примеры/ответы по формулам. Код возврата 1 при ошибках.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.content import ContentError, ContentRepository, load_formulas  # noqa: E402


def main() -> int:
    repo = ContentRepository()
    errors = repo.audit()
    try:
        page = load_formulas()
    except ContentError as exc:
        errors.append(str(exc))
        page = None

    for error in errors:
        print("ОШИБКА:", error)
    if errors:
        print(f"\nПроверка не пройдена: {len(errors)} ошибок.")
        return 1

    questions = sum(len(repo.get(topic.id).questions) for topic in repo.topics)
    examples = sum(len(repo.get(topic.id).examples) for topic in repo.topics)
    print(
        f"OK: {len(repo.topics)} тем, {questions} вопросов, "
        f"{examples} примеров, {len(page.groups) if page else 0} групп формул."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
