"""Пути к данным и константы приложения.

Модуль намеренно не импортирует Kivy: его используют и тесты, и сборщик
контента, и только потом — интерфейс.
"""
from __future__ import annotations

from pathlib import Path

APP_TITLE = "Электричество · ЕГЭ"
APP_VERSION = "1.0.0"

#: Тема считается пройденной, если лучший результат не ниже этого процента.
PASS_PERCENT = 60

#: Сколько уроков максимум держать в оперативной памяти.
#: JSON одного урока весит единицы килобайт, но кэш всё равно ограничен:
#: при переходе «теория → тест → теория» старые объекты вытесняются.
CONTENT_CACHE_LIMIT = 2

#: Допуск по умолчанию для числовых ответов (доля от эталона).
DEFAULT_NUMERIC_TOLERANCE = 0.02

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LESSONS_DIR = DATA_DIR / "lessons"
INDEX_FILE = DATA_DIR / "index.json"
FORMULAS_FILE = DATA_DIR / "formulas.json"
