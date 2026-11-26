"""Модели контента.

Все классы используют ``__slots__``: у экземпляров нет словаря ``__dict__``,
поэтому каждая тема/вопрос занимает заметно меньше памяти, чем обычный
Python-объект. Коллекции внутри моделей — кортежи, чтобы их нельзя было
случайно изменить во время показа.
"""
from __future__ import annotations

from typing import Any

from .units import format_number

CHOICE = "choice"
NUMERIC = "numeric"


class TopicMeta:
    """Краткая карточка темы из index.json (хранится всегда, она крошечная)."""

    __slots__ = ("id", "title", "subtitle", "minutes", "questions", "filename")

    def __init__(
        self,
        topic_id: str,
        title: str,
        subtitle: str,
        minutes: int,
        questions: int,
        filename: str,
    ) -> None:
        self.id = topic_id
        self.title = title
        self.subtitle = subtitle
        self.minutes = minutes
        self.questions = questions
        self.filename = filename

    @property
    def has_quiz(self) -> bool:
        return self.questions > 0


class Formula:
    __slots__ = ("name", "expr", "note")

    def __init__(self, name: str, expr: str, note: str = "") -> None:
        self.name = name
        self.expr = expr
        self.note = note


class FormulaGroup:
    __slots__ = ("title", "items")

    def __init__(self, title: str, items: tuple[Formula, ...]) -> None:
        self.title = title
        self.items = items


class FormulasPage:
    __slots__ = ("title", "subtitle", "groups")

    def __init__(
        self, title: str, subtitle: str, groups: tuple[FormulaGroup, ...]
    ) -> None:
        self.title = title
        self.subtitle = subtitle
        self.groups = groups


class Section:
    __slots__ = ("heading", "body", "diagram")

    def __init__(self, heading: str, body: str, diagram: str = "") -> None:
        self.heading = heading
        self.body = body
        self.diagram = diagram


class Example:
    """Разобранная задача: условие, шаги решения и ответ."""

    __slots__ = ("title", "given", "steps", "answer", "calc")

    def __init__(
        self,
        title: str,
        given: str,
        steps: tuple[str, ...],
        answer: str,
        calc: dict[str, Any] | None,
    ) -> None:
        self.title = title
        self.given = given
        self.steps = steps
        self.answer = answer
        self.calc = calc


class Question:
    __slots__ = (
        "id",
        "kind",
        "text",
        "options",
        "answer",
        "unit",
        "tolerance",
        "explanation",
        "hint",
        "calc",
    )

    def __init__(
        self,
        question_id: str,
        kind: str,
        text: str,
        options: tuple[str, ...],
        answer: Any,
        unit: str,
        tolerance: float,
        explanation: str,
        hint: str,
        calc: dict[str, Any] | None,
    ) -> None:
        self.id = question_id
        self.kind = kind
        self.text = text
        self.options = options
        self.answer = answer
        self.unit = unit
        self.tolerance = tolerance
        self.explanation = explanation
        self.hint = hint
        self.calc = calc

    # ------------------------------------------------------------------ quiz
    def is_correct(self, given: Any) -> bool:
        """Проверяет ответ ученика.

        Для ``choice`` ожидается индекс варианта (int), для ``numeric`` —
        строка/число; строка разбирается с поддержкой запятой и записи
        ``2,5·10^-3``.
        """
        if self.kind == CHOICE:
            if isinstance(given, bool):
                return False
            if isinstance(given, str):
                given = given.strip()
                if not given.isdigit():
                    return False
            try:
                return int(given) == int(self.answer)
            except (TypeError, ValueError):
                return False

        if self.kind == NUMERIC:
            from .units import is_close, parse_number

            parsed = parse_number(given)
            if parsed is None:
                return False
            return is_close(parsed, float(self.answer), rel=self.tolerance)
        return False

    def correct_text(self) -> str:
        if self.kind == CHOICE:
            index = int(self.answer)
            if 0 <= index < len(self.options):
                return self.options[index]
            return "—"
        text = format_number(float(self.answer))
        return f"{text} {self.unit}".strip()

    def given_text(self, given: Any) -> str:
        if self.kind == CHOICE:
            try:
                index = int(given)
            except (TypeError, ValueError):
                return "—"
            if 0 <= index < len(self.options):
                return self.options[index]
            return "—"
        if given is None:
            return "—"
        text = str(given).strip()
        return text or "—"


class Lesson:
    __slots__ = (
        "id",
        "title",
        "subtitle",
        "minutes",
        "sections",
        "formulas",
        "examples",
        "questions",
    )

    def __init__(
        self,
        lesson_id: str,
        title: str,
        subtitle: str,
        minutes: int,
        sections: tuple[Section, ...],
        formulas: tuple[Formula, ...],
        examples: tuple[Example, ...],
        questions: tuple[Question, ...],
    ) -> None:
        self.id = lesson_id
        self.title = title
        self.subtitle = subtitle
        self.minutes = minutes
        self.sections = sections
        self.formulas = formulas
        self.examples = examples
        self.questions = questions


class AnswerResult:
    __slots__ = ("question", "given_text", "correct")

    def __init__(self, question: Question, given_text: str, correct: bool) -> None:
        self.question = question
        self.given_text = given_text
        self.correct = correct


class QuizSummary:
    __slots__ = ("lesson_id", "title", "total", "correct", "percent", "wrongs")

    def __init__(
        self,
        lesson_id: str,
        title: str,
        total: int,
        correct: int,
        percent: int,
        wrongs: tuple[AnswerResult, ...],
    ) -> None:
        self.lesson_id = lesson_id
        self.title = title
        self.total = total
        self.correct = correct
        self.percent = percent
        self.wrongs = wrongs
