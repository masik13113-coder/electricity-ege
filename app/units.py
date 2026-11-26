"""Разбор и форматирование чисел так, как это принято в школе.

Ученик может ввести ответ по-разному: ``0,6``, ``0.6``, ``6·10^-1``,
``2,5*10^3``. Всё это приводится к ``float``. Ошибки ввода возвращают
``None`` вместо исключения — интерфейс показывает подсказку.
"""
from __future__ import annotations

import math
import re

_SUPERSCRIPT = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")

_PLAIN_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")
_EXP_RE = re.compile(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))[eE]([+-]?\d+)$")
_POW10_RE = re.compile(
    r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))\*10\^\(?([+-]?\d+)\)?$"
)
_POW10_ONLY_RE = re.compile(r"^10\^\(?([+-]?\d+)\)?$")
_SUPER_POWER_RE = re.compile(r"10([⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+)")
_SUPER_TO_ASCII = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")

_MINUS_VARIANTS = ("\u2212", "\u2013", "\u2014")
_MULT_VARIANTS = ("·", "×", "х", "x", "X")


def parse_number(raw: object) -> float | None:
    """Возвращает число или ``None``, если ввод не похож на число."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
        return value if math.isfinite(value) else None

    text = str(raw).strip()
    if not text:
        return None
    for dash in _MINUS_VARIANTS:
        text = text.replace(dash, "-")
    text = (
        text.replace("\u00a0", "")
        .replace("\u202f", "")
        .replace(" ", "")
        .replace(",", ".")
    )
    # «1·10⁻⁶» из подсказки ответа -> «1*10^-6»
    text = _SUPER_POWER_RE.sub(
        lambda match: "10^" + match.group(1).translate(_SUPER_TO_ASCII), text
    )
    for sign in _MULT_VARIANTS:
        text = text.replace(sign, "*")
    text = text.replace("**", "^")

    match = _PLAIN_RE.fullmatch(text)
    if match:
        return _finite(float(text))

    match = _EXP_RE.fullmatch(text)
    if match:
        try:
            return _finite(float(match.group(1)) * 10.0 ** int(match.group(2)))
        except (OverflowError, ValueError):
            return None

    match = _POW10_RE.fullmatch(text)
    if match:
        try:
            return _finite(float(match.group(1)) * 10.0 ** int(match.group(2)))
        except (OverflowError, ValueError):
            return None

    match = _POW10_ONLY_RE.fullmatch(text)
    if match:
        try:
            return _finite(10.0 ** int(match.group(1)))
        except (OverflowError, ValueError):
            return None

    try:
        return _finite(float(text))
    except (TypeError, ValueError, OverflowError):
        return None


def _finite(value: float) -> float | None:
    if not math.isfinite(value):
        return None
    return value


def is_close(
    value: float | None,
    expected: float | None,
    rel: float = 0.02,
    abs_epsilon: float = 1e-9,
) -> bool:
    """Сравнение с относительным допуском (по умолчанию 2 %)."""
    if value is None or expected is None:
        return False
    if not math.isfinite(value) or not math.isfinite(expected):
        return False
    tolerance = max(abs_epsilon, abs(expected) * max(0.0, rel))
    return abs(value - expected) <= tolerance


def format_number(value: float | None, sig: int = 3) -> str:
    """Короткая запись числа с запятой и, при необходимости, степенью 10.

    >>> format_number(0.6)
    '0,6'
    >>> format_number(0.0006)
    '6·10⁻⁴'
    """
    if value is None or not math.isfinite(value):
        return "—"
    if value == 0:
        return "0"

    absolute = abs(value)
    if 1e-3 <= absolute < 1e4:
        exponent = math.floor(math.log10(absolute))
        decimals = max(0, sig - 1 - exponent)
        text = f"{value:.{decimals}f}"
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        if text in ("", "-0", "-"):
            text = "0"
        return text.replace(".", ",")

    exponent = int(math.floor(math.log10(absolute)))
    mantissa = value / (10.0 ** exponent)
    if abs(mantissa) >= 9.995:
        mantissa /= 10.0
        exponent += 1
    decimals = max(0, sig - 1)
    text = f"{mantissa:.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    power = str(exponent).translate(_SUPERSCRIPT)
    return f"{text.replace('.', ',')}·10{power}"


def format_with_unit(value: float | None, unit: str, sig: int = 3) -> str:
    text = format_number(value, sig=sig)
    unit = (unit or "").strip()
    return f"{text} {unit}".strip()
