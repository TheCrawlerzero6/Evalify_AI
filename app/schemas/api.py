from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.domain import EstadoFlujo, ResultadoFinal


class ChatRequest(BaseModel):
    thread_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    response: str
    estado: EstadoFlujo
    criterios: List[str]
    proveedores: List[str]
    resultado_final: Optional[ResultadoFinal] = None
