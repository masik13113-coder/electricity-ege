"""Проверка разметки Kivy до запуска интерфейса.

Kivy разбирает ``[b]``, ``[sub]``, ``[sup]``, ``[color=#rrggbb]`` только при
``markup=True``. Если в тексте случайно окажется незакрытая скобка, метка
может отрисоваться неверно или «съесть» часть текста. Поэтому весь контент
проверяется при загрузке и в тестах.
"""
from __future__ import annotations

import re

_TAG_RE = re.compile(r"\[(/?)([A-Za-z][A-Za-z0-9_]*)(?:=([^\[\]]*))?\]")
_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

#: Тег -> обязателен ли параметр.
_ALLOWED_TAGS = {
    "b": False,
    "i": False,
    "u": False,
    "sub": False,
    "sup": False,
    "color": True,
}


def validate(text: object) -> tuple[str, ...]:
    """Возвращает список проблем разметки (пустой кортеж — всё хорошо)."""
    if not isinstance(text, str):
        return ("значение не является строкой",)

    problems: list[str] = []
    stack: list[str] = []
    outside: list[str] = []
    cursor = 0

    for match in _TAG_RE.finditer(text):
        outside.append(text[cursor : match.start()])
        closing, raw_name, value = match.group(1), match.group(2), match.group(3)
        name = raw_name.lower()

        if name not in _ALLOWED_TAGS:
            problems.append(f"неизвестный тег «{raw_name}»")
        elif closing:
            if value is not None:
                problems.append(f"у закрывающего тега «/{name}» не должно быть значения")
            if not stack:
                problems.append(f"лишний закрывающий тег «/{name}»")
            elif stack[-1] != name:
                problems.append(
                    f"тег «/{name}» закрывает не тот тег (ожидался «/{stack[-1]}»)"
                )
            else:
                stack.pop()
        else:
            if value is not None and not _ALLOWED_TAGS.get(name, False):
                problems.append(f"тег «{name}» не принимает значение")
            if name == "color":
                if value is None:
                    problems.append("тег color требует значение вида #RRGGBB")
                elif not _COLOR_RE.fullmatch(value):
                    problems.append(f"неверный цвет «{raw_name}={value}»")
            stack.append(name)
        cursor = match.end()

    outside.append(text[cursor:])

    for name in reversed(stack):
        problems.append(f"тег [{name}] не закрыт")

    tail = "".join(outside)
    if "[" in tail or "]" in tail:
        problems.append("в тексте есть квадратная скобка вне тега")
    if "&" in tail:
        problems.append("символ & в Kivy-разметке лучше не использовать")

    # Убираем повторы, сохраняя порядок.
    unique: list[str] = []
    for problem in problems:
        if problem not in unique:
            unique.append(problem)
    return tuple(unique)


def is_valid(text: object) -> bool:
    return not validate(text)


def strip_tags(text: str) -> str:
    """Убирает разрешённые теги — полезно для коротких превью."""
    return _TAG_RE.sub("", text)
