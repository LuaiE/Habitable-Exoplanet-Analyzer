import numpy as np
import pandas as pd
import pytest

from fetch_data import fill_derived, elim_bad_rows
from habitable import hz_edge, add_hz_edgeData, classify_type, add_data_quality, add_atmo_score, add_composition
from monte_carlo import get_sigma, simulate


# ---------- fetch_data.py ----------

def test_kepler_and_insolation_give_earth_values():
    earth = pd.DataFrame({"pl_orbper": [365.25], "st_mass": [1.0], "st_lum": [0.0],
                          "pl_orbsmax": [np.nan], "pl_insol": [np.nan]})
    result = fill_derived(earth)
    assert result["pl_orbsmax"].iloc[0] == pytest.approx(1.0, rel=1e-3)
    assert result["pl_insol"].iloc[0] == pytest.approx(1.0, rel=1e-3)
    assert result["pl_orbsmax_derived"].iloc[0]


def test_measured_values_are_not_overwritten():
    planet = pd.DataFrame({"pl_orbper": [100.0], "st_mass": [1.0], "st_lum": [0.0],
                           "pl_orbsmax": [0.7], "pl_insol": [0.5]})
    result = fill_derived(planet)
    assert result["pl_insol"].iloc[0] == 0.5
    assert not result["pl_insol_derived"].iloc[0]


def test_bad_rows_are_removed_and_disputed_are_flagged():
    planets = pd.DataFrame({
        "pl_name": ["good", "disputed", "negative radius", "not orbiting"],
        "pl_controv_flag": [0, 1, 0, 0],
        "pl_rade": [1.0, 1.0, -1.0, 1.0],
        "pl_orbeccen": [0.1, 0.1, 0.1, 1.2],
    })
    result = elim_bad_rows(planets)
    assert list(result["pl_name"]) == ["good", "disputed"]
    assert list(result["disputed"]) == [False, True]

# ---------- habitable.py ----------

def test_hz_edges_for_the_sun():
    assert hz_edge(5780, "runaway_greenhouse") == pytest.approx(1.107)
    assert hz_edge(5780, "max_greenhouse") == pytest.approx(0.356)


def test_cooler_stars_have_lower_hz_edges():
    assert hz_edge(3000, "runaway_greenhouse") < hz_edge(5780, "runaway_greenhouse")


def test_hz_classification():
    planets = pd.DataFrame({
        "pl_name": ["Earth", "TRAPPIST-1 e", "too hot", "brown dwarf host"],
        "st_teff": [5780, 2566, 5780, 2000],
        "pl_insol": [1.0, 0.646, 5.0, 0.5],
    })
    result = add_hz_edgeData(planets)
    assert list(result["within_conservative"]) == [True, True, False, False]


def test_size_classes():
    planets = pd.DataFrame({"pl_rade": [1.0, 1.7, 3.0]})
    result = classify_type(planets)
    assert list(result["pl_type"]) == ["rocky", "uncertain", "gaseous"]


def test_data_quality_tiers():
    planets = pd.DataFrame({
        "pl_radeerr1": [0.01, 0.01, np.nan, 0.01],
        "pl_bmassprov": ["Mass", "M-R relationship", "Mass", "Mass"],
        "pl_bmasselim": [0, 0, 0, 1],
    })
    result = add_data_quality(planets)
    assert list(result["data_quality"]) == ["high", "medium", "low", "medium"]

def test_atmosphere_score_solar_system():
    planets = pd.DataFrame({"pl_name": ["Earth", "Mars"], "pl_bmasse": [1.0, 0.107],
                            "pl_rade": [1.0, 0.532], "pl_insol": [1.0, 0.43]})
    result = add_atmo_score(planets)
    assert result["atmo_score"].iloc[0] == pytest.approx(1.0)
    assert result["atmo_score"].iloc[1] == pytest.approx(0.094, abs=0.005)


# ---------- monte_carlo.py ----------

def make_planet(rade, insol, teff, rade_err=0.01, insol_err=0.01, teff_err=10):
    return pd.Series({
        "pl_rade": rade, "pl_radeerr1": rade_err, "pl_radeerr2": -rade_err,
        "pl_insol": insol, "pl_insolerr1": insol_err, "pl_insolerr2": -insol_err,
        "st_teff": teff, "st_tefferr1": teff_err, "st_tefferr2": -teff_err,
        "data_quality": "high", "composition": "unknown", "pl_bmasse": 1.0, 
        "pl_bmasseerr1": 0.05, "pl_bmasseerr2": -0.05,
    })


def test_sigma_averages_the_two_errors():
    planet = make_planet(1.0, 1.0, 5780)
    planet["pl_radeerr1"], planet["pl_radeerr2"] = 0.04, -0.02
    assert get_sigma(planet, "pl_rade") == pytest.approx(0.03)


def test_missing_radius_error_uses_30_percent():
    planet = make_planet(1.0, 1.0, 5780, rade_err=np.nan)
    assert get_sigma(planet, "pl_rade") == pytest.approx(0.30)


def test_precise_earth_is_a_strong_candidate():
    result = simulate(make_planet(1.0, 1.0, 5780), np.random.default_rng(0))
    assert result["p_strong"] > 0.99


def test_gas_giant_is_never_rocky():
    result = simulate(make_planet(11.0, 1.0, 5780), np.random.default_rng(0))
    assert result["p_rocky"] < 0.001

def test_same_seed_gives_same_results():
    planet = make_planet(1.4, 1.0, 5780, rade_err=0.1)
    first = simulate(planet, np.random.default_rng(42))
    second = simulate(planet, np.random.default_rng(42))
    assert first == second

def test_composition():
    planets = pd.DataFrame({
        "pl_name": ["Earth", "LHS 1140 b", "puffy", "no mass", "impossible"],
        "pl_rade": [1.0, 1.73, 2.5, 1.0, 1.4],
        "pl_bmasse": [1.0, 5.6, 5.0, 1.0, 35.0],
        "data_quality": ["high", "high", "high", "low", "high"],
    })
    result = add_composition(planets)
    assert list(result["composition"]) == ["rocky", "water_world", "gas_envelope", "unknown", "unknown"]


def test_water_world_counts_as_having_a_surface():
    planet = make_planet(1.73, 0.43, 3096, rade_err=0.025)
    planet["composition"] = "water_world"
    planet["pl_bmasse"], planet["pl_bmasseerr1"], planet["pl_bmasseerr2"] = 5.6, 0.19, -0.19
    result = simulate(planet, np.random.default_rng(0))
    assert result["p_surface"] > 0.95
    assert result["p_rocky"] < 0.05