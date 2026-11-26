import math

import pytest

from app.units import format_number, format_with_unit, is_close, parse_number


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("2,5", 2.5),
        ("2.5", 2.5),
        ("0,6", 0.6),
        (" 3 ", 3.0),
        ("−3", -3.0),
        ("-3", -3.0),
        ("2,5·10^-3", 0.0025),
        ("2,5·10^3", 2500.0),
        ("2.5*10^3", 2500.0),
        ("2.5x10^3", 2500.0),
        ("2.5e-3", 0.0025),
        ("1·10⁻⁶", 1e-6),
        ("2·10⁶", 2e6),
        ("10⁻⁶", 1e-6),
        ("10^3", 1000.0),
        ("1 200", 1200.0),
        ("0,0006", 0.0006),
        (".5", 0.5),
        ("5.", 5.0),
        (7, 7.0),
        (7.5, 7.5),
    ],
)
def test_parse_number_accepts_forms(raw, expected):
    assert parse_number(raw) == pytest.approx(expected)


@pytest.mark.parametrize(
    "raw",
    ["", "   ", None, "abc", "1,2,3", "inf", "nan", True, False, "--3"],
)
def test_parse_number_rejects_garbage(raw):
    assert parse_number(raw) is None


def test_parse_number_rejects_infinity():
    assert parse_number("1e999") is None


def test_is_close_relative_tolerance():
    assert is_close(0.61, 0.6, rel=0.02)
    assert is_close(0.59, 0.6, rel=0.02)
    assert not is_close(0.7, 0.6, rel=0.02)
    assert is_close(0.0, 0.0)
    assert not is_close(None, 1.0)
    assert not is_close(float("nan"), 1.0)


def test_is_close_zero_answer_requires_near_zero():
    assert is_close(1e-12, 0.0)
    assert not is_close(0.001, 0.0)


@pytest.mark.parametrize(
    "value, expected",
    [
        (0.6, "0,6"),
        (1.5, "1,5"),
        (3, "3"),
        (1200, "1200"),
        (0.025, "0,025"),
        (0.0006, "6·10⁻⁴"),
        (96485, "9,65·10⁴"),
        (-3, "-3"),
        (0, "0"),
    ],
)
def test_format_number(value, expected):
    assert format_number(value) == expected


def test_format_number_handles_float_noise():
    assert format_number(0.30000000000000004) == "0,3"
    assert format_number(2.0000000000000004) == "2"


def test_format_number_edge_cases():
    assert format_number(None) == "—"
    assert format_number(math.inf) == "—"
    assert format_with_unit(180, "В") == "180 В"
    assert format_with_unit(0.5, "") == "0,5"
