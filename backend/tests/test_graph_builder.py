from __future__ import annotations

from app.schemas.domain import CriterioEvaluado
from app.services.graph_builder import (
    _build_score_simple,
    _has_valid_web_observations,
    _normalize_criterios,
    _serialize_analisis_individual,
)


def test_normalize_criterios_dedups_and_limits() -> None:
    criterios = _normalize_criterios([" Precio ", "precio", "SOPORTE", "integraciones", "extra"])
    assert criterios == ["precio", "soporte", "integraciones"]


def test_has_valid_web_observations_filters_error_prefix() -> None:
    assert _has_valid_web_observations(["Se encontro documentacion oficial."], "precio")
    assert not _has_valid_web_observations(["Error consultando web para precio: timeout"], "precio")
    assert not _has_valid_web_observations([], "precio")


def test_serialize_analisis_individual_normalizes_inputs() -> None:
    data = {
        "precio": CriterioEvaluado(
            criterio="precio",
            clasificacion="alto",
            evidencia="Costo competitivo",
            origen="web",
        ),
        "soporte": {
            "criterio": "soporte",
            "clasificacion": "medio",
            "evidencia": "Soporte en horario habil",
            "origen": "usuario",
        },
        "seguridad": 123,
    }

    serialized = _serialize_analisis_individual(data)

    assert serialized["precio"]["clasificacion"] == "alto"
    assert serialized["soporte"]["origen"] == "usuario"
    assert serialized["seguridad"]["clasificacion"] == "medio"


def test_build_score_simple_handles_missing_criteria_data() -> None:
    providers = [
        {
            "nombre": "Proveedor A",
            "analisis_individual": {
                "precio": {
                    "criterio": "precio",
                    "clasificacion": "alto",
                    "evidencia": "e1",
                    "origen": "web",
                }
            },
        },
        {
            "nombre": "Proveedor B",
            "analisis_individual": {
                "precio": {
                    "criterio": "precio",
                    "clasificacion": "bajo",
                    "evidencia": "e2",
                    "origen": "web",
                },
                "reputacion": {
                    "criterio": "reputacion",
                    "clasificacion": "bajo",
                    "evidencia": "e3",
                    "origen": "web",
                },
            },
        },
    ]

    scores = _build_score_simple(providers, ["precio"])

    assert scores["Proveedor A"] == 5
    assert scores["Proveedor B"] == 2
