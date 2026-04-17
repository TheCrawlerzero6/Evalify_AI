from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

EstadoFlujo = Literal[
    "ingesta",
    "criterios",
    "enriquecimiento",
    "analisis",
    "comparacion",
    "fin",
    "esperando_proveedores",
    "esperando_criterios",
]


class SourceRef(BaseModel):
    titulo: str = ""
    url: str
    snippet: str = ""
    criterio: str
    categoria: Optional[str] = None


class CriterioEvaluado(BaseModel):
    criterio: str
    clasificacion: Literal["alto", "medio", "bajo"]
    evidencia: str
    origen: Literal["documento", "web"]


class ProveedorAnalisis(BaseModel):
    nombre: str
    texto_original: str = ""
    busqueda_web: Dict[str, List[str]] = Field(default_factory=dict)
    fuentes_web: Dict[str, List[SourceRef]] = Field(default_factory=dict)
    analisis_individual: Dict[str, CriterioEvaluado] = Field(default_factory=dict)


class ResultadoFinal(BaseModel):
    diferencias: List[str] = Field(default_factory=list)
    similitudes: List[str] = Field(default_factory=list)
    ventajas: List[str] = Field(default_factory=list)
    desventajas: List[str] = Field(default_factory=list)
    conclusion: str = ""
    score_simple: Dict[str, int] = Field(default_factory=dict)


class ProveedorInput(BaseModel):
    nombre: str
    texto: str


class SessionStateModel(BaseModel):
    input: str = ""
    output: str = ""
    estado: EstadoFlujo = "ingesta"
    criterios: List[str] = Field(default_factory=list)
    proveedores: List[ProveedorAnalisis] = Field(default_factory=list)
    resultado_final: Optional[ResultadoFinal] = None
    pending_inputs: List[ProveedorInput] = Field(default_factory=list)


class UserExtraction(BaseModel):
    proveedores: List[ProveedorInput] = Field(default_factory=list)
    criterios: List[str] = Field(default_factory=list)
    quiere_comparar: bool = False


class ProviderCriterionAssessment(BaseModel):
    evaluaciones: List[CriterioEvaluado] = Field(default_factory=list)
