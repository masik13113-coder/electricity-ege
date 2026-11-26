"""Логика прохождения теста.

Сессия хранит только ссылки на вопросы открытого урока и несколько
результатов — не копирует весь контент. После выхода с экрана теста
сессия уничтожается вместе с виджетами.
"""
from __future__ import annotations

import random
from typing import Any

from .models import AnswerResult, Lesson, Question, QuizSummary


class QuizSession:
    __slots__ = (
        "lesson",
        "questions",
        "position",
        "correct_count",
        "_answered",
        "_results",
    )

    def __init__(
        self,
        lesson: Lesson,
        *,
        shuffle: bool = True,
        seed: int | None = None,
    ) -> None:
        if not lesson.questions:
            raise ValueError("в этой теме нет вопросов для теста")
        questions = list(lesson.questions)
        if shuffle:
            random.Random(seed).shuffle(questions)
        self.lesson = lesson
        self.questions: tuple[Question, ...] = tuple(questions)
        self.position = 0
        self.correct_count = 0
        self._answered = False
        self._results: list[AnswerResult] = []

    # ------------------------------------------------------------------ state
    @property
    def current(self) -> Question:
        return self.questions[self.position]

    @property
    def total(self) -> int:
        return len(self.questions)

    @property
    def number(self) -> int:
        """Номер текущего вопроса, начиная с 1."""
        return self.position + 1

    @property
    def answered(self) -> bool:
        return self._answered

    @property
    def is_last(self) -> bool:
        return self.position >= self.total - 1

    @property
    def finished(self) -> bool:
        return self._answered and self.is_last

    @property
    def results(self) -> tuple[AnswerResult, ...]:
        """Уже данные ответы (для экрана разбора ошибок)."""
        return tuple(self._results)

    @property
    def percent(self) -> int:
        if not self.total:
            return 0
        return int((self.correct_count * 100 + self.total // 2) // self.total)

    # ----------------------------------------------------------------- actions
    def submit(self, value: Any) -> bool:
        """Проверяет ответ и запоминает результат. Возвращает, верно ли."""
        if self._answered:
            raise RuntimeError("ответ на этот вопрос уже дан")
        question = self.current
        correct = question.is_correct(value)
        self._results.append(
            AnswerResult(question, question.given_text(value), correct)
        )
        if correct:
            self.correct_count += 1
        self._answered = True
        return correct

    def advance(self) -> bool:
        """Переходит к следующему вопросу. False — тест закончен."""
        if not self._answered:
            raise RuntimeError("сначала нужно ответить на вопрос")
        if self.is_last:
            return False
        self.position += 1
        self._answered = False
        return True

    def summary(self) -> QuizSummary:
        if not self.finished:
            raise RuntimeError("тест ещё не завершён")
        wrongs = tuple(result for result in self._results if not result.correct)
        return QuizSummary(
            lesson_id=self.lesson.id,
            title=self.lesson.title,
            total=self.total,
            correct=self.correct_count,
            percent=self.percent,
            wrongs=wrongs,
        )
