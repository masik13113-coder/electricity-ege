"""Загрузка и строгая проверка учебного контента.

Контент лежит в ``data/lessons/*.json`` по одному файлу на тему. Это сделано
специально: приложение читает с диска только открытую тему, а не весь курс
целиком. Проверка схемы и формул выполняется при загрузке, поэтому битый
JSON или арифметическая опечатка не доходят до ученика.

Кэш ограничен ``config.CONTENT_CACHE_LIMIT`` уроками (по умолчанию 2):
открытие новой темы вытесняет старую из памяти.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path
from typing import Any

from . import config, formulas, markup, units
from .models import (
    CHOICE,
    NUMERIC,
    Example,
    Formula,
    FormulaGroup,
    FormulasPage,
    Lesson,
    Question,
    Section,
    TopicMeta,
)

_DIAGRAMS = frozenset({"series", "parallel", "emf"})
_KINDS = frozenset({CHOICE, NUMERIC})

_INDEX_KEYS = frozenset({"version", "title", "lessons"})
_TOPIC_KEYS = frozenset({"id", "title", "subtitle", "minutes", "questions", "file"})
_LESSON_KEYS = frozenset(
    {
        "id",
        "title",
        "subtitle",
        "minutes",
        "sections",
        "formulas",
        "examples",
        "questions",
    }
)
_SECTION_KEYS = frozenset({"h", "p", "diagram"})
_FORMULA_KEYS = frozenset({"name", "expr", "note"})
_EXAMPLE_KEYS = frozenset({"title", "given", "steps", "answer", "calc"})
_QUESTION_KEYS = frozenset(
    {"id", "kind", "text", "options", "answer", "unit", "tolerance", "explanation", "hint", "calc"}
)
_CALC_KEYS = frozenset({"formula", "args", "value", "scale"})
_FORMULAS_KEYS = frozenset({"title", "subtitle", "groups"})
_GROUP_KEYS = frozenset({"title", "items"})


class ContentError(ValueError):
    """Понятная человеку ошибка в учебных данных."""


# --------------------------------------------------------------------- helpers
def _ctx_error(ctx: str, message: str) -> ContentError:
    return ContentError(f"{ctx}: {message}")


def _check_keys(raw: dict[str, Any], allowed: frozenset[str], ctx: str) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise _ctx_error(ctx, "неизвестные поля: " + ", ".join(unknown))


def _required_dict(raw: Any, ctx: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise _ctx_error(ctx, "ожидался объект JSON")
    return raw


def _required_list(raw: Any, ctx: str, *, allow_empty: bool = False) -> list[Any]:
    if not isinstance(raw, list):
        raise _ctx_error(ctx, "ожидался массив JSON")
    if not raw and not allow_empty:
        raise _ctx_error(ctx, "массив не должен быть пустым")
    return raw


def _text(
    raw: dict[str, Any],
    key: str,
    ctx: str,
    *,
    required: bool = True,
    check_markup: bool = True,
    max_len: int = 4000,
) -> str:
    value = raw.get(key)
    if value is None:
        if required:
            raise _ctx_error(ctx, f"нет обязательного текстового поля «{key}»")
        return ""
    if not isinstance(value, str):
        raise _ctx_error(ctx, f"поле «{key}» должно быть строкой")
    value = value.strip()
    if required and not value:
        raise _ctx_error(ctx, f"поле «{key}» не должно быть пустым")
    if len(value) > max_len:
        raise _ctx_error(ctx, f"поле «{key}» слишком длинное")
    if check_markup and value:
        problems = markup.validate(value)
        if problems:
            raise _ctx_error(ctx, f"поле «{key}»: " + "; ".join(problems))
    return value


def _slug(raw: dict[str, Any], key: str, ctx: str) -> str:
    value = _text(raw, key, ctx, check_markup=False, max_len=64)
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-_")
    if not set(value) <= allowed:
        raise _ctx_error(ctx, f"поле «{key}» может содержать только a-z, 0-9, «-» и «_»")
    return value


def _number(
    raw: dict[str, Any],
    key: str,
    ctx: str,
    *,
    required: bool = True,
    positive: bool = False,
    integer: bool = False,
    default: float | None = None,
) -> float:
    value = raw.get(key)
    if value is None:
        if required:
            raise _ctx_error(ctx, f"нет обязательного числового поля «{key}»")
        return 0.0 if default is None else float(default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _ctx_error(ctx, f"поле «{key}» должно быть числом")
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise _ctx_error(ctx, f"поле «{key}» должно быть конечным числом")
    if integer and int(value) != value:
        raise _ctx_error(ctx, f"поле «{key}» должно быть целым числом")
    if positive and value <= 0:
        raise _ctx_error(ctx, f"поле «{key}» должно быть положительным")
    return value


def _calc(raw: dict[str, Any], ctx: str, *, expected: bool) -> dict[str, Any] | None:
    value = raw.get("calc")
    if value is None:
        return None
    calc = _required_dict(value, ctx)
    _check_keys(calc, _CALC_KEYS, ctx)
    if not isinstance(calc.get("formula"), str):
        raise _ctx_error(ctx, "в calc.formula должна быть строка")
    if "args" in calc:
        args = calc["args"]
        if not isinstance(args, dict):
            raise _ctx_error(ctx, "calc.args должен быть объектом")
        for key in args:
            if not isinstance(key, str):
                raise _ctx_error(ctx, "ключи calc.args должны быть строками")
    try:
        computed = formulas.compute_scaled(calc)
    except formulas.FormulaError as exc:
        raise _ctx_error(ctx, f"ошибка в calc: {exc}") from exc

    if expected:
        if "value" not in calc:
            raise _ctx_error(ctx, "в calc нужно поле value — эталонный ответ")
        declared = _number(calc, "value", ctx)
        if not units.is_close(computed, declared, rel=1e-6, abs_epsilon=1e-12):
            raise _ctx_error(
                ctx,
                "calc.value не совпадает с расчётом по формуле: "
                f"в JSON {declared:g}, по формуле {computed:g}",
            )
    elif "value" in calc:
        declared = _number(calc, "value", ctx)
        if not units.is_close(computed, declared, rel=1e-6, abs_epsilon=1e-12):
            raise _ctx_error(
                ctx,
                f"calc.value {declared:g} не совпадает с формулой ({computed:g})",
            )
    return calc


def _read_json(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContentError(f"не удалось прочитать «{path.name}»: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ContentError(
            f"«{path.name}»: ошибка JSON в строке {exc.lineno}, колонке {exc.colno}: {exc.msg}"
        ) from exc


# ------------------------------------------------------------------ построение
def build_lesson(raw: Any, meta: TopicMeta | None = None) -> Lesson:
    """Проверяет JSON урока и превращает его в неизменяемую модель."""
    raw = _required_dict(raw, "урок")
    _check_keys(raw, _LESSON_KEYS, "урок")

    lesson_id = _slug(raw, "id", "урок")
    if meta is not None and lesson_id != meta.id:
        raise _ctx_error(
            "урок",
            f"id «{lesson_id}» не совпадает с id «{meta.id}» в index.json",
        )

    title = _text(raw, "title", f"урок {lesson_id}", max_len=120)
    subtitle = _text(raw, "subtitle", f"урок {lesson_id}", max_len=200)
    minutes = int(
        _number(
            raw,
            "minutes",
            f"урок {lesson_id}",
            required=False,
            positive=True,
            integer=True,
            default=meta.minutes if meta is not None else 10,
        )
    )

    sections = _build_sections(raw.get("sections"), lesson_id)
    formula_items = _build_formulas(raw.get("formulas", []), lesson_id)
    examples = _build_examples(raw.get("examples", []), lesson_id)
    questions = _build_questions(raw.get("questions", []), lesson_id)

    if meta is not None and len(questions) != meta.questions:
        raise _ctx_error(
            f"урок {lesson_id}",
            f"в index.json указано {meta.questions} вопросов, а в файле {len(questions)}",
        )

    return Lesson(
        lesson_id=lesson_id,
        title=title,
        subtitle=subtitle,
        minutes=minutes,
        sections=sections,
        formulas=formula_items,
        examples=examples,
        questions=questions,
    )


def _build_sections(value: Any, lesson_id: str) -> tuple[Section, ...]:
    items = _required_list(value, f"урок {lesson_id}: sections")
    sections: list[Section] = []
    for index, item in enumerate(items, start=1):
        ctx = f"урок {lesson_id}, раздел {index}"
        raw = _required_dict(item, ctx)
        _check_keys(raw, _SECTION_KEYS, ctx)
        heading = _text(raw, "h", ctx, max_len=160)
        body = _text(raw, "p", ctx, max_len=6000)
        diagram = _text(raw, "diagram", ctx, required=False, check_markup=False, max_len=20)
        if diagram and diagram not in _DIAGRAMS:
            raise _ctx_error(
                ctx, f"неизвестная схема «{diagram}», доступны: {', '.join(sorted(_DIAGRAMS))}"
            )
        sections.append(Section(heading, body, diagram))
    return tuple(sections)


def _build_formulas(value: Any, lesson_id: str) -> tuple[Formula, ...]:
    if value is None:
        return ()
    items = _required_list(value, f"урок {lesson_id}: formulas", allow_empty=True)
    result: list[Formula] = []
    for index, item in enumerate(items, start=1):
        ctx = f"урок {lesson_id}, формула {index}"
        raw = _required_dict(item, ctx)
        _check_keys(raw, _FORMULA_KEYS, ctx)
        result.append(
            Formula(
                name=_text(raw, "name", ctx, max_len=120),
                expr=_text(raw, "expr", ctx, max_len=200),
                note=_text(raw, "note", ctx, required=False, max_len=300),
            )
        )
    return tuple(result)


def _build_examples(value: Any, lesson_id: str) -> tuple[Example, ...]:
    if value is None:
        return ()
    items = _required_list(value, f"урок {lesson_id}: examples", allow_empty=True)
    result: list[Example] = []
    for index, item in enumerate(items, start=1):
        ctx = f"урок {lesson_id}, пример {index}"
        raw = _required_dict(item, ctx)
        _check_keys(raw, _EXAMPLE_KEYS, ctx)
        steps_raw = _required_list(raw.get("steps"), f"{ctx}: steps")
        steps: list[str] = []
        for step_index, step in enumerate(steps_raw, start=1):
            step_ctx = f"{ctx}, шаг {step_index}"
            if not isinstance(step, str) or not step.strip():
                raise _ctx_error(step_ctx, "шаг должен быть непустой строкой")
            step_text = step.strip()
            problems = markup.validate(step_text)
            if problems:
                raise _ctx_error(step_ctx, "; ".join(problems))
            steps.append(step_text)
        result.append(
            Example(
                title=_text(raw, "title", ctx, max_len=160),
                given=_text(raw, "given", ctx, max_len=600),
                steps=tuple(steps),
                answer=_text(raw, "answer", ctx, max_len=400),
                calc=_calc(raw, ctx, expected=True),
            )
        )
    return tuple(result)


def _build_questions(value: Any, lesson_id: str) -> tuple[Question, ...]:
    if value is None:
        return ()
    items = _required_list(value, f"урок {lesson_id}: questions", allow_empty=True)
    result: list[Question] = []
    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        ctx = f"урок {lesson_id}, вопрос {index}"
        raw = _required_dict(item, ctx)
        _check_keys(raw, _QUESTION_KEYS, ctx)
        question_id = _slug(raw, "id", ctx)
        if question_id in seen:
            raise _ctx_error(ctx, f"повторяющийся id вопроса «{question_id}»")
        seen.add(question_id)

        kind = raw.get("kind")
        if kind not in _KINDS:
            raise _ctx_error(ctx, f"kind должен быть «{CHOICE}» или «{NUMERIC}»")
        text = _text(raw, "text", ctx, max_len=800)
        explanation = _text(raw, "explanation", ctx, max_len=1500)
        hint = _text(raw, "hint", ctx, required=False, max_len=500)
        calc = _calc(raw, ctx, expected=False)

        if kind == CHOICE:
            options_raw = _required_list(raw.get("options"), f"{ctx}: options")
            if not 2 <= len(options_raw) <= 6:
                raise _ctx_error(ctx, "должно быть от 2 до 6 вариантов ответа")
            options: list[str] = []
            for option_index, option in enumerate(options_raw, start=1):
                option_ctx = f"{ctx}, вариант {option_index}"
                if not isinstance(option, str) or not option.strip():
                    raise _ctx_error(option_ctx, "вариант должен быть непустой строкой")
                option_text = option.strip()
                problems = markup.validate(option_text)
                if problems:
                    raise _ctx_error(option_ctx, "; ".join(problems))
                options.append(option_text)
            answer = _number(raw, "answer", ctx, integer=True)
            if not 0 <= int(answer) < len(options):
                raise _ctx_error(ctx, "answer должен указывать на существующий вариант")
            if "unit" in raw or "tolerance" in raw:
                raise _ctx_error(ctx, "unit и tolerance допустимы только для числового вопроса")
            result.append(
                Question(
                    question_id=question_id,
                    kind=CHOICE,
                    text=text,
                    options=tuple(options),
                    answer=int(answer),
                    unit="",
                    tolerance=0.0,
                    explanation=explanation,
                    hint=hint,
                    calc=calc,
                )
            )
        else:
            answer = _number(raw, "answer", ctx)
            unit = _text(raw, "unit", ctx, required=False, check_markup=False, max_len=40)
            tolerance = _number(
                raw,
                "tolerance",
                ctx,
                required=False,
                positive=True,
                default=config.DEFAULT_NUMERIC_TOLERANCE,
            )
            if not 0.0001 <= tolerance <= 0.5:
                raise _ctx_error(ctx, "tolerance должна быть в пределах от 0,0001 до 0,5")
            if calc is None:
                raise _ctx_error(
                    ctx, "у числового вопроса обязательно поле calc — иначе ответ нельзя проверить"
                )
            try:
                computed = formulas.compute_scaled(calc)
            except formulas.FormulaError as exc:  # уже проверено, но пусть будет явно
                raise _ctx_error(ctx, str(exc)) from exc
            if not units.is_close(computed, answer, rel=1e-6, abs_epsilon=1e-12):
                raise _ctx_error(
                    ctx,
                    "answer не совпадает с расчётом по формуле: "
                    f"в JSON {answer:g}, по формуле {computed:g}",
                )
            if "options" in raw:
                raise _ctx_error(ctx, "options допустимы только для вопроса с выбором ответа")
            result.append(
                Question(
                    question_id=question_id,
                    kind=NUMERIC,
                    text=text,
                    options=(),
                    answer=answer,
                    unit=unit,
                    tolerance=tolerance,
                    explanation=explanation,
                    hint=hint,
                    calc=calc,
                )
            )
    return tuple(result)


# ----------------------------------------------------------------------- index
def load_index(data_dir: Path | str | None = None) -> tuple[TopicMeta, ...]:
    base = Path(data_dir) if data_dir is not None else config.DATA_DIR
    raw = _required_dict(_read_json(base / "index.json"), "index.json")
    _check_keys(raw, _INDEX_KEYS, "index.json")
    lessons_raw = _required_list(raw.get("lessons"), "index.json: lessons")

    topics: list[TopicMeta] = []
    ids: set[str] = set()
    files: set[str] = set()
    for index, item in enumerate(lessons_raw, start=1):
        ctx = f"index.json, тема {index}"
        entry = _required_dict(item, ctx)
        _check_keys(entry, _TOPIC_KEYS, ctx)
        topic_id = _slug(entry, "id", ctx)
        if topic_id in ids:
            raise _ctx_error(ctx, f"повторяющийся id «{topic_id}»")
        ids.add(topic_id)

        filename = _text(entry, "file", ctx, check_markup=False, max_len=120)
        if Path(filename).name != filename or not filename.endswith(".json"):
            raise _ctx_error(ctx, "file должен быть именем файла с расширением .json")
        if filename in files:
            raise _ctx_error(ctx, f"файл «{filename}» указан дважды")
        files.add(filename)
        lesson_path = base / "lessons" / filename
        if not lesson_path.is_file():
            raise _ctx_error(ctx, f"файл «{filename}» не найден в data/lessons")

        topics.append(
            TopicMeta(
                topic_id=topic_id,
                title=_text(entry, "title", ctx, max_len=120),
                subtitle=_text(entry, "subtitle", ctx, max_len=200),
                minutes=int(_number(entry, "minutes", ctx, positive=True, integer=True)),
                questions=int(_number(entry, "questions", ctx, integer=True)),
                filename=filename,
            )
        )
    return tuple(topics)


# ------------------------------------------------------------------ формулы-лист
def load_formulas(data_dir: Path | str | None = None) -> FormulasPage:
    base = Path(data_dir) if data_dir is not None else config.DATA_DIR
    raw = _required_dict(_read_json(base / "formulas.json"), "formulas.json")
    _check_keys(raw, _FORMULAS_KEYS, "formulas.json")
    groups_raw = _required_list(raw.get("groups"), "formulas.json: groups")
    groups: list[FormulaGroup] = []
    for group_index, item in enumerate(groups_raw, start=1):
        ctx = f"formulas.json, группа {group_index}"
        group = _required_dict(item, ctx)
        _check_keys(group, _GROUP_KEYS, ctx)
        items_raw = _required_list(group.get("items"), f"{ctx}: items")
        formulas_list: list[Formula] = []
        for formula_index, formula_item in enumerate(items_raw, start=1):
            formula_ctx = f"{ctx}, формула {formula_index}"
            formula_raw = _required_dict(formula_item, formula_ctx)
            _check_keys(formula_raw, _FORMULA_KEYS, formula_ctx)
            formulas_list.append(
                Formula(
                    name=_text(formula_raw, "name", formula_ctx, max_len=120),
                    expr=_text(formula_raw, "expr", formula_ctx, max_len=200),
                    note=_text(formula_raw, "note", formula_ctx, required=False, max_len=300),
                )
            )
        groups.append(
            FormulaGroup(
                title=_text(group, "title", ctx, max_len=120),
                items=tuple(formulas_list),
            )
        )
    return FormulasPage(
        title=_text(raw, "title", "formulas.json", max_len=120),
        subtitle=_text(raw, "subtitle", "formulas.json", max_len=200),
        groups=tuple(groups),
    )


# ------------------------------------------------------------------ repository
class ContentRepository:
    """Ленивый доступ к урокам с маленьким LRU-кэшем."""

    def __init__(
        self,
        data_dir: Path | str | None = None,
        cache_limit: int = config.CONTENT_CACHE_LIMIT,
    ) -> None:
        if cache_limit < 1:
            raise ValueError("cache_limit должен быть >= 1")
        self._base = Path(data_dir) if data_dir is not None else config.DATA_DIR
        self._cache_limit = cache_limit
        self._cache: OrderedDict[str, Lesson] = OrderedDict()
        self._topics = load_index(self._base)
        self._by_id = {topic.id: topic for topic in self._topics}

    @property
    def topics(self) -> tuple[TopicMeta, ...]:
        return self._topics

    @property
    def total_questions(self) -> int:
        return sum(topic.questions for topic in self._topics)

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    def topic(self, lesson_id: str) -> TopicMeta:
        try:
            return self._by_id[lesson_id]
        except KeyError as exc:
            raise ContentError(f"тема «{lesson_id}» не найдена в index.json") from exc

    def get(self, lesson_id: str) -> Lesson:
        cached = self._cache.get(lesson_id)
        if cached is not None:
            self._cache.move_to_end(lesson_id)
            return cached

        topic = self.topic(lesson_id)
        path = self._base / "lessons" / topic.filename
        raw = _read_json(path)
        lesson = build_lesson(raw, topic)
        self._cache[lesson_id] = lesson
        self._cache.move_to_end(lesson_id)
        while len(self._cache) > self._cache_limit:
            self._cache.popitem(last=False)
        return lesson

    def release(self, lesson_id: str | None = None) -> None:
        """Освобождает память: один урок или весь кэш."""
        if lesson_id is None:
            self._cache.clear()
        else:
            self._cache.pop(lesson_id, None)

    def audit(self) -> list[str]:
        """Проверяет все файлы, не останавливаясь на первой ошибке."""
        errors: list[str] = []
        for topic in self._topics:
            try:
                lesson = build_lesson(
                    _read_json(self._base / "lessons" / topic.filename), topic
                )
            except ContentError as exc:
                errors.append(str(exc))
                continue
            if len(lesson.questions) != topic.questions:
                errors.append(
                    f"тема {topic.id}: вопросов {len(lesson.questions)}, "
                    f"а в index.json {topic.questions}"
                )
        return errors
