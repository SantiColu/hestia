"""Environment parameters and their validation (docs/etapas/environment.md, ADR 0021, 0023)."""

import math
from typing import Any

import pytest

from hestia_core.environment.orbit import Orbit, nominal_altitude_m, nominal_inclination_rad
from hestia_core.environment.parameters import (
    DESIGN_VALUE_SOURCE,
    DesignValues,
    DesignValueSource,
    EclipseModel,
    EnvironmentParameters,
    design_value_band,
    environment_defaults,
    resolve_design_values,
    validate_environment_parameters,
)
from hestia_core.forms import ProblemCode
from hestia_core.mission import MissionArtifact

C = ProblemCode
DAY = 86_400.0


SSO = {"type": "sso", "altitude": 600e3, "ltan": "10:30"}
NADIR = {
    "name": "Apuntado nadir",
    "primary_axis": "+Z",
    "primary_target": "nadir",
    "secondary_axis": "+X",
    "secondary_target": "velocity",
}


def mission() -> MissionArtifact:
    return MissionArtifact.model_validate(
        {"general": {"launch_date": "2028-03-01", "design_life": 2 * 365.25 * DAY}}
    )


def params(**sections: Any) -> EnvironmentParameters:
    """Parameters with a valid SSO orbit and one attitude mode, changed by ``sections``."""
    return EnvironmentParameters.model_validate(
        {"orbit": SSO, "attitude_modes": [NADIR], **sections}
    )


def codes(
    parameters: EnvironmentParameters, context: MissionArtifact | None = None
) -> set[tuple[str, ProblemCode]]:
    return {(p.path, p.code) for p in validate_environment_parameters(parameters, context)}


def test_defaults_only_lack_the_orbit_and_the_attitude() -> None:
    defaults = environment_defaults()
    assert defaults.schema_version == 2
    assert defaults.orbit == Orbit()
    assert defaults.attitude_modes == []
    assert defaults.design_values.solar_constant == 1361.0
    assert defaults.design_values.albedo_min is None  # table by inclination
    assert defaults.sampling.mission_step == DAY
    assert defaults.sampling.orbit_samples == 120
    assert defaults.sampling.eclipse_model is EclipseModel.CYLINDRICAL
    assert defaults.custom_conditions == []
    missing = {
        ("orbit.altitude", C.REQUIRED),
        ("orbit.ltan", C.REQUIRED),
        ("attitude_modes", C.REQUIRED),
    }
    assert codes(defaults) == missing
    assert codes(defaults, mission()) == missing
    assert codes(params()) == set()


def test_schema_marks_defaults_units_and_sources() -> None:
    schema = EnvironmentParameters.model_json_schema()
    solar = schema["$defs"]["DesignValues"]["properties"]["solar_constant"]
    assert solar["x-default"] == 1361.0 and solar["x-unit"] == "W/m²"
    assert "ECSS-E-ST-10-04C" in solar["x-default-source"]
    albedo = schema["$defs"]["DesignValues"]["properties"]["albedo_min"]
    assert albedo["x-default-source"] == DESIGN_VALUE_SOURCE
    step = schema["$defs"]["Sampling"]["properties"]["mission_step"]
    assert (step["x-unit"], step["x-display-unit"]) == ("s", "días")
    ltan = schema["$defs"]["Dispersion"]["properties"]["ltan_dispersion"]
    assert (ltan["x-unit"], ltan["x-display-unit"]) == ("s", "min")
    assert ltan["x-show-if"] == {"orbit.type": ["sso"]}
    eol = schema["$defs"]["Dispersion"]["properties"]["eol_altitude"]
    assert eol["x-show-if"] == {"orbit.type": ["sso", "keplerian"]}
    assert schema["properties"]["custom_conditions"]["x-add-label"] == "Agregar condición"
    assert schema["properties"]["attitude_modes"]["x-add-label"] == "Agregar modo de actitud"
    assert list(schema["properties"])[1:3] == ["orbit", "attitude_modes"]  # first in the form
    assert schema["additionalProperties"] is False


def test_provisional_design_values_by_inclination() -> None:
    # Provisional single band (TODO: NASA TM-2001-211221): albedo 0.25 to 0.35, OLR 218 to 258 W/m².
    for inclination in (0.0, math.radians(51.6), math.radians(98.0), math.pi):
        band = design_value_band(inclination)
        assert (band.albedo_min, band.albedo_max) == (0.25, 0.35)
        assert (band.olr_min_w_m2, band.olr_max_w_m2) == (218.0, 258.0)
        assert "NASA TM-2001-211221" in band.source and "provisorio" in band.source.lower()


def test_resolution_keeps_entered_values_and_fills_the_rest() -> None:
    resolved = resolve_design_values(DesignValues(albedo_max=0.4), math.radians(98))
    assert resolved.albedo_max.value == 0.4
    assert resolved.albedo_max.source is DesignValueSource.ENTERED
    assert resolved.albedo_min.value == 0.25
    assert resolved.albedo_min.source is DesignValueSource.LIBRARY
    assert resolved.albedo_min.reference == DESIGN_VALUE_SOURCE
    assert resolved.solar_constant.value == 1361.0
    assert resolved.solar_constant.source is DesignValueSource.ENTERED  # the form default


def test_nominal_orbit_of_each_type() -> None:
    sso = Orbit.model_validate(SSO)
    assert nominal_altitude_m(sso) == 600e3
    sso_inclination = nominal_inclination_rad(sso)
    assert sso_inclination is not None and math.degrees(sso_inclination) == pytest.approx(
        97.8, abs=0.1
    )  # SMAD fig. 6-7: ≈ 97.8° at 600 km
    kepler = Orbit.model_validate(
        {"type": "keplerian", "perigee_altitude": 500e3, "inclination": 0.9}
    )
    assert nominal_altitude_m(kepler) == 500e3 and nominal_inclination_rad(kepler) == 0.9
    geo = Orbit.model_validate({"type": "geo"})
    assert nominal_altitude_m(geo) == 35_786e3 and nominal_inclination_rad(geo) == 0.0


def test_design_values_ranges_and_order() -> None:
    bad = params(
        design_values={
            "solar_constant": 0,
            "albedo_min": -0.1,
            "albedo_max": 1.2,
            "olr_min": 0,
        }
    )
    assert codes(bad) == {
        ("design_values.solar_constant", C.MIN),
        ("design_values.albedo_min", C.MIN),
        ("design_values.albedo_max", C.MAX),
        ("design_values.olr_min", C.MIN),
    }
    assert codes(params(design_values={"solar_constant": None})) == {
        ("design_values.solar_constant", C.REQUIRED)
    }
    swapped = params(design_values={"albedo_min": 0.4, "albedo_max": 0.3, "olr_min": 260})
    # An empty bound is the table's for the orbit's inclination: OLR min 260 > table max 258.
    assert codes(swapped) == {
        ("design_values.albedo_max", C.ORDER),
        ("design_values.olr_max", C.ORDER),
    }


def test_dispersion_fields_follow_the_orbit_type() -> None:
    all_fields = params(
        dispersion={"ltan_dispersion": 600, "eol_altitude": 500e3, "geo_max_inclination": 0.01}
    )
    assert codes(all_fields) == {("dispersion.geo_max_inclination", C.NOT_ALLOWED)}
    kepler = {"type": "keplerian", "perigee_altitude": 700e3, "inclination": 0.9}
    assert codes(params(orbit=kepler, dispersion=all_fields.dispersion.model_dump())) == {
        ("dispersion.ltan_dispersion", C.NOT_ALLOWED),
        ("dispersion.geo_max_inclination", C.NOT_ALLOWED),
    }
    geo = params(orbit={"type": "geo"}, dispersion=all_fields.dispersion.model_dump())
    assert codes(geo) == {
        ("dispersion.ltan_dispersion", C.NOT_ALLOWED),
        ("dispersion.eol_altitude", C.NOT_ALLOWED),
    }


def test_dispersion_limits() -> None:
    assert codes(params(dispersion={"ltan_dispersion": -1})) == {
        ("dispersion.ltan_dispersion", C.MIN)
    }
    geo = params(orbit={"type": "geo"}, dispersion={"geo_max_inclination": -0.1})
    assert codes(geo) == {("dispersion.geo_max_inclination", C.MIN)}
    assert codes(params(dispersion={"eol_altitude": 90e3})) == {("dispersion.eol_altitude", C.MIN)}
    assert codes(params(dispersion={"eol_altitude": 550e3})) == set()
    assert codes(params(dispersion={"eol_altitude": 650e3})) == {("dispersion.eol_altitude", C.MAX)}
    kepler = {
        "type": "keplerian",
        "perigee_altitude": 600e3,
        "apogee_altitude": 700e3,
        "inclination": 0.9,
    }
    above = params(orbit=kepler, dispersion={"eol_altitude": 650e3})
    assert codes(above) == {("dispersion.eol_altitude", C.MAX)}  # above the perigee


def test_sampling_limits() -> None:
    assert codes(params(sampling={"mission_step": 0, "orbit_samples": 35})) == {
        ("sampling.mission_step", C.MIN),
        ("sampling.orbit_samples", C.MIN),
    }
    assert codes(params(sampling={"orbit_samples": 3601})) == {("sampling.orbit_samples", C.MAX)}
    assert codes(params(sampling={"orbit_samples": 36})) == set()
    assert codes(params(sampling={"orbit_samples": 3600})) == set()
    long_step = params(sampling={"mission_step": 3 * 365.25 * DAY})
    assert codes(long_step) == set()
    assert codes(long_step, mission()) == {("sampling.mission_step", C.MAX)}
    empty = params(sampling={"mission_step": None, "orbit_samples": None, "eclipse_model": None})
    assert codes(empty) == {
        ("sampling.mission_step", C.REQUIRED),
        ("sampling.orbit_samples", C.REQUIRED),
        ("sampling.eclipse_model", C.REQUIRED),
    }


def test_custom_conditions() -> None:
    conditions = params(
        custom_conditions=[
            {"name": "β = 30°", "beta": math.radians(30)},
            {"name": " β  = 30° ", "beta": math.radians(91), "altitude": 50e3},
            {"beta": math.radians(-91)},
            {"name": "Sin β"},
        ]
    )
    assert codes(conditions) == {
        ("custom_conditions[1].name", C.DUPLICATE_NAME),
        ("custom_conditions[1].beta", C.MAX),
        ("custom_conditions[1].altitude", C.MIN),
        ("custom_conditions[2].name", C.REQUIRED),
        ("custom_conditions[2].beta", C.MIN),
        ("custom_conditions[3].beta", C.REQUIRED),
    }
