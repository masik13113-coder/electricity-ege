"""Физические формулы темы «Электричество» в единицах СИ.

Зачем отдельный модуль: каждый числовой пример в контенте ссылается на
формулу и аргументы. При загрузке урока (и в тестах) приложение заново
считает ответ и сравнивает с тем, что написано в JSON. Опечатка в числе
или единицах сразу превращается в понятную ошибку, а не в неверный ответ
ученику.
"""
from __future__ import annotations

import math
from typing import Any, Callable

#: Электрическая постоянная, Ф/м (в школьных задачах округляют до 8,85·10⁻¹²).
EPS0 = 8.85e-12
#: Коэффициент Кулона, Н·м²/Кл².
K_COULOMB = 9.0e9
#: Элементарный заряд, Кл.
E_CHARGE = 1.6e-19
#: Масса электрона, кг.
M_ELECTRON = 9.1e-31
#: Постоянная Фарадея, Кл/моль.
FARADAY = 96485.0


class FormulaError(ValueError):
    """Формула не найдена или аргументы не подходят."""


def _positive(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"«{name}» должно быть положительным числом")
    return value


# --------------------------------------------------------------- электростатика
def coulomb_force(q1: float, q2: float, r: float, eps: float = 1.0) -> float:
    """Сила взаимодействия двух точечных зарядов, Н (eps — проницаемость среды)."""
    r = _positive("r", r)
    eps = _positive("eps", eps)
    return K_COULOMB * abs(float(q1) * float(q2)) / (eps * r * r)


def field_strength(q: float, r: float, eps: float = 1.0) -> float:
    """Напряжённость поля точечного заряда, В/м."""
    r = _positive("r", r)
    eps = _positive("eps", eps)
    return K_COULOMB * abs(float(q)) / (eps * r * r)


def potential(q: float, r: float, eps: float = 1.0) -> float:
    """Потенциал поля точечного заряда (φ = 0 на бесконечности), В."""
    r = _positive("r", r)
    eps = _positive("eps", eps)
    return K_COULOMB * float(q) / (eps * r)


def potential_energy(q: float, phi: float) -> float:
    """Потенциальная энергия заряда в точке с потенциалом phi, Дж."""
    return float(q) * float(phi)


def work_in_field(q: float, voltage: float) -> float:
    """Работа поля при перемещении заряда между точками с разностью U, Дж."""
    return float(q) * float(voltage)


def voltage_from_work(work: float, q: float) -> float:
    """Разность потенциалов через работу поля, В."""
    q = float(q)
    if q == 0:
        raise ValueError("заряд не может быть нулевым")
    return float(work) / q


def uniform_field(voltage: float, d: float) -> float:
    """Напряжённость однородного поля E = U/d, В/м."""
    d = _positive("d", d)
    return float(voltage) / d


def field_force(q: float, field: float) -> float:
    """Сила, действующая на заряд в поле: F = q·E, Н."""
    return float(q) * float(field)


def field_voltage(field: float, d: float) -> float:
    """Разность потенциалов в однородном поле U = E·d, В."""
    return float(field) * float(d)


def charge_after_contact(q1: float, q2: float) -> float:
    """Заряд каждого из двух одинаковых шариков после касания, Кл."""
    return (float(q1) + float(q2)) / 2.0


def field_between_opposite(q: float, a: float) -> float:
    """Поле в середине между зарядами +q и −q, удалёнными на 2a, В/м."""
    a = _positive("a", a)
    return 2.0 * K_COULOMB * abs(float(q)) / (a * a)


# --------------------------------------------------------------------- ёмкость
def capacitance_flat(eps: float, area: float, d: float) -> float:
    """Ёмкость плоского конденсатора, Ф (eps — относительная проницаемость)."""
    area = _positive("area", area)
    d = _positive("d", d)
    eps = _positive("eps", eps)
    return EPS0 * eps * area / d


def capacitor_charge(capacitance: float, voltage: float) -> float:
    """Заряд конденсатора q = C·U, Кл."""
    return float(capacitance) * float(voltage)


def capacitor_energy(capacitance: float, voltage: float) -> float:
    """Энергия заряженного конденсатора W = C·U²/2, Дж."""
    return float(capacitance) * float(voltage) ** 2 / 2.0


def capacitor_energy_from_charge(charge: float, capacitance: float) -> float:
    """Энергия конденсатора через заряд W = q²/(2C), Дж."""
    capacitance = _positive("capacitance", capacitance)
    return float(charge) ** 2 / (2.0 * capacitance)


def capacitance_series(c1: float, c2: float) -> float:
    """Последовательное соединение двух конденсаторов, Ф."""
    c1 = _positive("c1", c1)
    c2 = _positive("c2", c2)
    return c1 * c2 / (c1 + c2)


def capacitance_parallel(c1: float, c2: float) -> float:
    """Параллельное соединение двух конденсаторов, Ф."""
    c1 = _positive("c1", c1)
    c2 = _positive("c2", c2)
    return c1 + c2


# ---------------------------------------------------------------- постоянный ток
def current_strength(charge: float, t: float) -> float:
    """Сила тока I = q/t, А."""
    t = _positive("t", t)
    return float(charge) / t


def charge_from_current(I: float, t: float) -> float:
    """Заряд, прошедший через сечение q = I·t, Кл."""
    t = _positive("t", t)
    return float(I) * t


def resistance(rho: float, length: float, area: float) -> float:
    """Сопротивление проводника R = ρ·l/S, Ом."""
    length = _positive("length", length)
    area = _positive("area", area)
    return float(rho) * length / area


def resistance_heated(r0: float, alpha: float, dt: float) -> float:
    """Сопротивление металла при нагреве R = R₀(1 + α·Δt), Ом."""
    r0 = _positive("r0", r0)
    return r0 * (1.0 + float(alpha) * float(dt))


def resistance_series(r1: float, r2: float) -> float:
    """Последовательное соединение двух резисторов, Ом."""
    return float(r1) + float(r2)


def resistance_parallel(r1: float, r2: float) -> float:
    """Параллельное соединение двух резисторов, Ом."""
    r1 = _positive("r1", r1)
    r2 = _positive("r2", r2)
    return r1 * r2 / (r1 + r2)


def circuit_mixed(r1: float, r2: float, r3: float) -> float:
    """R1 и R2 параллельно, результат последовательно с R3, Ом."""
    return resistance_parallel(r1, r2) + float(r3)


def ohm_current(voltage: float, R: float) -> float:
    """Закон Ома для участка цепи I = U/R, А."""
    R = _positive("R", R)
    return float(voltage) / R


def ohm_voltage(I: float, R: float) -> float:
    """Напряжение на участке U = I·R, В."""
    return float(I) * float(R)


def voltage_divider(U: float, R1: float, R2: float) -> float:
    """Напряжение на R1 при последовательном соединении R1 и R2, В."""
    R1 = _positive("R1", R1)
    R2 = _positive("R2", R2)
    return float(U) * R1 / (R1 + R2)


# ------------------------------------------------------------- работа и мощность
def power_ui(U: float, I: float) -> float:
    """Мощность P = U·I, Вт."""
    return float(U) * float(I)


def current_from_power(P: float, U: float) -> float:
    """Сила тока через мощность и напряжение I = P/U, А."""
    U = _positive("U", U)
    return float(P) / U


def power_i2r(I: float, R: float) -> float:
    """Мощность P = I²·R, Вт."""
    return float(I) ** 2 * float(R)


def power_u2r(U: float, R: float) -> float:
    """Мощность P = U²/R, Вт."""
    R = _positive("R", R)
    return float(U) ** 2 / R


def resistance_from_power(U: float, P: float) -> float:
    """Сопротивление по напряжению и мощности R = U²/P, Ом."""
    P = _positive("P", P)
    return float(U) ** 2 / P


def joule_lenz(I: float, R: float, t: float) -> float:
    """Количество теплоты Q = I²·R·t, Дж."""
    t = _positive("t", t)
    return float(I) ** 2 * float(R) * t


# ------------------------------------------------------------- полная цепь, ЭДС
def emf_current(emf: float, R: float, r: float) -> float:
    """Ток в полной цепи I = ε/(R + r), А."""
    R = float(R)
    r = float(r)
    if R < 0 or r <= 0 or R + r <= 0:
        raise ValueError("сопротивления должны быть неотрицательными, r > 0")
    return float(emf) / (R + r)


def terminal_voltage(emf: float, I: float, r: float) -> float:
    """Напряжение на клеммах источника U = ε − I·r, В."""
    return float(emf) - float(I) * float(r)


def source_efficiency(emf: float, R: float, r: float) -> float:
    """КПД источника в долях: η = R/(R + r)."""
    emf = float(emf)
    if emf <= 0:
        raise ValueError("ЭДС должна быть положительной")
    R = float(R)
    r = float(r)
    if R < 0 or r < 0 or R + r <= 0:
        raise ValueError("некорректные сопротивления")
    return R / (R + r)


def max_external_power(emf: float, r: float) -> float:
    """Максимальная мощность во внешней цепи P = ε²/(4r), Вт."""
    emf = float(emf)
    if emf <= 0:
        raise ValueError("ЭДС должна быть положительной")
    r = _positive("r", r)
    return emf * emf / (4.0 * r)


def energy_cost(power_kw: float, hours: float, price: float) -> float:
    """Стоимость электроэнергии: P(кВт)·t(ч)·тариф."""
    hours = _positive("hours", hours)
    if float(power_kw) < 0 or float(price) < 0:
        raise ValueError("мощность и тариф не могут быть отрицательными")
    return float(power_kw) * hours * float(price)


# ------------------------------------------------------------- ток в электролите
def electrolysis_mass(
    M: float, n: float, I: float, t: float, F: float = FARADAY
) -> float:
    """Масса вещества по закону Фарадея m = M·I·t/(n·F), кг."""
    t = _positive("t", t)
    F = _positive("F", F)
    n = _positive("n", n)
    if float(M) <= 0:
        raise ValueError("молярная масса должна быть положительной")
    return float(M) * float(I) * t / (n * F)


def electrolysis_mass_k(k: float, I: float, t: float) -> float:
    """Масса через электрохимический эквивалент: m = k·I·t, кг."""
    t = _positive("t", t)
    return float(k) * float(I) * t


# --------------------------------------------------------------------- частицы
def charge_count(q: float, e: float = E_CHARGE) -> float:
    """Число элементарных зарядов N = q/e."""
    e = _positive("e", e)
    return abs(float(q)) / e


def electron_speed(voltage: float, e: float = E_CHARGE, m: float = M_ELECTRON) -> float:
    """Скорость электрона после разгона разностью потенциалов U, м/с."""
    e = _positive("e", e)
    m = _positive("m", m)
    kinetic = 2.0 * e * abs(float(voltage)) / m
    return math.sqrt(kinetic)


#: Имя формулы -> функция. Имена используются в JSON-поле ``calc.formula``.
REGISTRY: dict[str, Callable[..., float]] = {
    "coulomb_force": coulomb_force,
    "field_strength": field_strength,
    "potential": potential,
    "potential_energy": potential_energy,
    "work_in_field": work_in_field,
    "voltage_from_work": voltage_from_work,
    "uniform_field": uniform_field,
    "field_force": field_force,
    "field_voltage": field_voltage,
    "charge_after_contact": charge_after_contact,
    "field_between_opposite": field_between_opposite,
    "capacitance_flat": capacitance_flat,
    "capacitor_charge": capacitor_charge,
    "capacitor_energy": capacitor_energy,
    "capacitor_energy_from_charge": capacitor_energy_from_charge,
    "capacitance_series": capacitance_series,
    "capacitance_parallel": capacitance_parallel,
    "current_strength": current_strength,
    "charge_from_current": charge_from_current,
    "resistance": resistance,
    "resistance_heated": resistance_heated,
    "resistance_series": resistance_series,
    "resistance_parallel": resistance_parallel,
    "circuit_mixed": circuit_mixed,
    "ohm_current": ohm_current,
    "ohm_voltage": ohm_voltage,
    "voltage_divider": voltage_divider,
    "power_ui": power_ui,
    "current_from_power": current_from_power,
    "power_i2r": power_i2r,
    "power_u2r": power_u2r,
    "resistance_from_power": resistance_from_power,
    "joule_lenz": joule_lenz,
    "emf_current": emf_current,
    "terminal_voltage": terminal_voltage,
    "source_efficiency": source_efficiency,
    "max_external_power": max_external_power,
    "electrolysis_mass": electrolysis_mass,
    "electrolysis_mass_k": electrolysis_mass_k,
    "charge_count": charge_count,
    "electron_speed": electron_speed,
    "energy_cost": energy_cost,
}


def compute(calc: dict[str, Any]) -> float:
    """Считает значение из компактного описания ``{"formula": ..., "args": ...}``."""
    if not isinstance(calc, dict):
        raise FormulaError("описание расчёта должно быть объектом")
    name = calc.get("formula")
    if not isinstance(name, str) or name not in REGISTRY:
        raise FormulaError(f"неизвестная формула: {name!r}")
    args = calc.get("args", {})
    if not isinstance(args, dict):
        raise FormulaError("поле args должно быть объектом")
    for key, value in args.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise FormulaError(f"аргумент «{key}» должен быть числом")
        if not math.isfinite(float(value)):
            raise FormulaError(f"аргумент «{key}» должен быть конечным числом")
    try:
        value = float(REGISTRY[name](**args))
    except TypeError as exc:
        raise FormulaError(f"неверные аргументы для {name}: {exc}") from exc
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        raise FormulaError(f"не удалось вычислить {name}: {exc}") from exc
    if not math.isfinite(value):
        raise FormulaError(f"{name} дала не конечный результат")
    return value


def compute_scaled(calc: dict[str, Any]) -> float:
    """То же, что :func:`compute`, но с множителем ``calc["scale"]``.

    Множитель нужен, когда ответ в задаче удобнее дать не в СИ, например
    «1,5 мкФ»: формула считает в фарадах, а ``scale = 1e6`` переводит
    результат в микрофарады.
    """
    value = compute(calc)
    scale = calc.get("scale", 1.0)
    if isinstance(scale, bool) or not isinstance(scale, (int, float)):
        raise FormulaError("scale должен быть числом")
    scale = float(scale)
    if not math.isfinite(scale) or scale <= 0:
        raise FormulaError("scale должен быть положительным конечным числом")
    result = value * scale
    if not math.isfinite(result):
        raise FormulaError("после умножения на scale получилось не конечное число")
    return result
