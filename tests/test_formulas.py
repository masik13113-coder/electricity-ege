import math

import pytest

from app import formulas
from app.formulas import FormulaError, compute, compute_scaled


def test_coulomb_force_vacuum():
    assert compute(
        {
            "formula": "coulomb_force",
            "args": {"q1": 2e-6, "q2": 3e-6, "r": 0.3},
        }
    ) == pytest.approx(0.6)


def test_coulomb_force_in_medium():
    value = compute(
        {
            "formula": "coulomb_force",
            "args": {"q1": 2e-6, "q2": 3e-6, "r": 0.3, "eps": 2},
        }
    )
    assert value == pytest.approx(0.3)


def test_field_and_potential_of_point_charge():
    assert compute(
        {"formula": "field_strength", "args": {"q": 2e-9, "r": 0.3}}
    ) == pytest.approx(200)
    assert compute(
        {"formula": "potential", "args": {"q": 6e-9, "r": 0.3}}
    ) == pytest.approx(180)


def test_field_between_opposite_charges():
    value = compute(
        {
            "formula": "field_between_opposite",
            "args": {"q": 1e-9, "a": 0.1},
        }
    )
    assert value == pytest.approx(1800)


def test_capacitor_formulas():
    assert compute(
        {
            "formula": "capacitance_flat",
            "args": {"eps": 1, "area": 0.01, "d": 0.001},
        }
    ) == pytest.approx(8.85e-11)
    assert compute(
        {
            "formula": "capacitor_energy",
            "args": {"capacitance": 4e-6, "voltage": 200},
        }
    ) == pytest.approx(0.08)
    assert compute(
        {
            "formula": "capacitance_series",
            "args": {"c1": 2e-6, "c2": 6e-6},
        }
    ) == pytest.approx(1.5e-6)
    assert compute(
        {
            "formula": "capacitance_parallel",
            "args": {"c1": 2e-6, "c2": 6e-6},
        }
    ) == pytest.approx(8e-6)


def test_current_and_resistance():
    assert compute(
        {"formula": "current_strength", "args": {"charge": 12, "t": 4}}
    ) == pytest.approx(3)
    assert compute(
        {
            "formula": "resistance",
            "args": {"rho": 1.7e-8, "length": 10, "area": 0.5e-6},
        }
    ) == pytest.approx(0.34)
    assert compute(
        {"formula": "resistance_series", "args": {"r1": 4, "r2": 6}}
    ) == pytest.approx(10)
    assert compute(
        {"formula": "resistance_parallel", "args": {"r1": 4, "r2": 6}}
    ) == pytest.approx(2.4)


def test_mixed_circuit():
    value = compute(
        {
            "formula": "circuit_mixed",
            "args": {"r1": 6, "r2": 12, "r3": 2},
        }
    )
    assert value == pytest.approx(6)


def test_power_and_joule_lenz():
    assert compute(
        {"formula": "power_ui", "args": {"U": 12, "I": 2}}
    ) == pytest.approx(24)
    assert compute(
        {"formula": "joule_lenz", "args": {"I": 2, "R": 5, "t": 10}}
    ) == pytest.approx(200)
    assert compute(
        {"formula": "energy_cost", "args": {"power_kw": 2, "hours": 3, "price": 5}}
    ) == pytest.approx(30)


def test_emf_formulas():
    assert compute(
        {"formula": "emf_current", "args": {"emf": 12, "R": 5, "r": 1}}
    ) == pytest.approx(2)
    assert compute(
        {"formula": "terminal_voltage", "args": {"emf": 12, "I": 2, "r": 1}}
    ) == pytest.approx(10)
    assert compute(
        {"formula": "source_efficiency", "args": {"emf": 12, "R": 5, "r": 1}}
    ) == pytest.approx(5 / 6)
    assert compute(
        {"formula": "max_external_power", "args": {"emf": 12, "r": 2}}
    ) == pytest.approx(18)


def test_electrolysis():
    value = compute(
        {
            "formula": "electrolysis_mass",
            "args": {"M": 0.064, "n": 2, "I": 2, "t": 1800},
        }
    )
    assert value == pytest.approx(1.1939679742965228e-3)
    assert compute(
        {
            "formula": "electrolysis_mass_k",
            "args": {"k": 3.3e-7, "I": 2, "t": 1000},
        }
    ) == pytest.approx(6.6e-4)


def test_electron_speed_is_below_light_speed():
    speed = compute({"formula": "electron_speed", "args": {"voltage": 100}})
    assert speed == pytest.approx(5.93e6, rel=1e-3)
    assert speed < 3e8


def test_compute_scaled_for_micro_units():
    calc = {
        "formula": "capacitance_series",
        "args": {"c1": 2e-6, "c2": 6e-6},
        "scale": 1e6,
    }
    assert compute_scaled(calc) == pytest.approx(1.5)


def test_compute_scaled_default_scale_is_one():
    calc = {"formula": "power_ui", "args": {"U": 10, "I": 2}}
    assert compute_scaled(calc) == pytest.approx(20)


@pytest.mark.parametrize(
    "calc",
    [
        {"formula": "unknown", "args": {}},
        {"formula": "coulomb_force", "args": {"q1": 1, "q2": 1, "r": 0}},
        {"formula": "coulomb_force", "args": {"q1": "1", "q2": 1, "r": 1}},
        {"formula": "coulomb_force", "args": {"q1": True, "q2": 1, "r": 1}},
        {"formula": "power_ui", "args": {"U": 1}},
        {"formula": "power_ui", "args": {"U": 1, "I": 2}, "scale": 0},
        {"formula": "power_ui", "args": {"U": 1, "I": 2}, "scale": "x"},
        "not a dict",
    ],
)
def test_compute_errors(calc):
    with pytest.raises(FormulaError):
        compute_scaled(calc)


def test_registry_contains_content_formulas():
    expected = {
        "coulomb_force",
        "field_strength",
        "potential",
        "capacitance_flat",
        "capacitor_energy",
        "resistance",
        "resistance_parallel",
        "ohm_current",
        "power_ui",
        "joule_lenz",
        "emf_current",
        "electrolysis_mass",
    }
    assert expected <= set(formulas.REGISTRY)
    assert all(callable(item) for item in formulas.REGISTRY.values())


def test_constants_have_school_values():
    assert formulas.K_COULOMB == pytest.approx(9e9)
    assert formulas.E_CHARGE == pytest.approx(1.6e-19)
    assert formulas.M_ELECTRON == pytest.approx(9.1e-31)
    assert formulas.FARADAY == pytest.approx(96485)
    assert math.isclose(formulas.EPS0, 8.85e-12)
