from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.integrations.documents.pdf_reader import extract_pdf_text
from app.schemas.api import ChatRequest, ChatResponse
from app.schemas.domain import SessionStateModel
from app.services.graph_builder import UPLOAD_PREFIX, get_session_state, invoke_graph

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request) -> ChatResponse:
    graph_app = request.app.state.graph
    try:
        state = invoke_graph(graph_app, req.thread_id, req.message)
        parsed = SessionStateModel.model_validate(state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error procesando el chat: {exc}") from exc

    return ChatResponse(
        response=parsed.output,
        estado=parsed.estado,
        criterios=parsed.criterios,
        proveedores=[provider.nombre for provider in parsed.proveedores],
        resultado_final=parsed.resultado_final,
    )


@router.get("/session/{thread_id}")
def session_state(thread_id: str, request: Request) -> dict:
    graph_app = request.app.state.graph
    state = get_session_state(graph_app, thread_id)
    return SessionStateModel.model_validate(state).model_dump()


@router.post("/upload")
async def upload(
    request: Request,
    thread_id: str = Form(...),
    provider_name: str = Form("proveedor_sin_nombre"),
    text: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
) -> dict:
    if not text and not file:
        raise HTTPException(status_code=400, detail="Debes enviar al menos text o file.")

    merged_texts = []
    if text and text.strip():
        merged_texts.append(text.strip())

    if file:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Solo se admite PDF en el campo file.")
        raw = await file.read()
        extracted = extract_pdf_text(raw)
        if extracted:
            merged_texts.append(extracted)

    payload_text = "\n\n".join(merged_texts).strip()
    if not payload_text:
        raise HTTPException(status_code=400, detail="No se pudo extraer texto util del contenido recibido.")

    payload = {"provider_name": provider_name.strip() or "proveedor_sin_nombre", "text": payload_text}
    command = f"{UPLOAD_PREFIX}{json.dumps(payload, ensure_ascii=False)}"
    graph_app = request.app.state.graph
    state = invoke_graph(graph_app, thread_id, command)
    parsed = SessionStateModel.model_validate(state)

    return {
        "status": "ok",
        "message": "Contenido incorporado a la sesion.",
        "estado": parsed.estado,
        "pending_inputs": len(parsed.pending_inputs),
        "providers_detected": [provider.nombre for provider in parsed.proveedores],
        "extracted_chars": len(payload_text),
    }
