from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pypdf.errors import PdfReadError

from app.integrations.pdf_reader import extract_pdf_text
from app.schemas.api import ChatRequest, ChatResponse
from app.schemas.domain import SessionStateModel
from app.services.graph_builder import UPLOAD_PREFIX, get_session_state, invoke_graph

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict:
    logger.info("Health check solicitado")
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request) -> ChatResponse:
    logger.info("Solicitud /chat thread_id=%s message_len=%d", req.thread_id, len(req.message))
    graph_app = request.app.state.graph
    try:
        state = invoke_graph(graph_app, req.thread_id, req.message)
        parsed = SessionStateModel.model_validate(state)
    except Exception as exc:
        logger.exception("Error procesando /chat", exc_info=exc)
        raise HTTPException(status_code=500, detail="Error interno procesando la solicitud de chat.") from exc

    output_text = (parsed.output or "").strip()
    output_preview = output_text.replace("\n", " ")
    if len(output_preview) > 220:
        output_preview = output_preview[:220] + "..."

    logger.info(
        "Respuesta /chat thread_id=%s estado=%s proveedores=%d criterios=%d output_chars=%d has_resultado_final=%s output_preview=%s",
        req.thread_id,
        parsed.estado,
        len(parsed.proveedores),
        len(parsed.criterios),
        len(output_text),
        bool(parsed.resultado_final),
        output_preview,
    )

    return ChatResponse(
        response=parsed.output,
        estado=parsed.estado,
        criterios=parsed.criterios,
        proveedores=[provider.nombre for provider in parsed.proveedores],
        resultado_final=parsed.resultado_final,
    )


@router.get("/session/{thread_id}")
def session_state(thread_id: str, request: Request) -> dict:
    logger.info("Solicitud /session thread_id=%s", thread_id)
    graph_app = request.app.state.graph
    state = get_session_state(graph_app, thread_id)
    parsed = SessionStateModel.model_validate(state)
    logger.info(
        "Respuesta /session thread_id=%s estado=%s proveedores=%d criterios=%d",
        thread_id,
        parsed.estado,
        len(parsed.proveedores),
        len(parsed.criterios),
    )
    return parsed.model_dump()


@router.post("/upload")
async def upload(
    request: Request,
    thread_id: str = Form(...),
    provider_name: str = Form("proveedor_sin_nombre"),
    text: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
) -> dict:
    logger.info(
        "Solicitud /upload thread_id=%s provider=%s has_text=%s has_file=%s",
        thread_id,
        provider_name,
        bool(text and text.strip()),
        bool(file),
    )
    if not text and not file:
        raise HTTPException(status_code=400, detail="Debes enviar al menos text o file.")

    merged_texts = []
    if text and text.strip():
        merged_texts.append(text.strip())

    if file:
        filename = (file.filename or "").lower().strip()
        if not filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Solo se admite PDF en el campo file.")
        try:
            raw = await file.read()
            extracted = extract_pdf_text(raw)
            if extracted:
                merged_texts.append(extracted)
        except PdfReadError as exc:
            logger.warning("No se pudo leer PDF en /upload", exc_info=exc)
            raise HTTPException(status_code=400, detail="El archivo PDF es invalido o esta corrupto.") from exc
        except Exception as exc:
            logger.exception("Error inesperado al procesar PDF en /upload", exc_info=exc)
            raise HTTPException(status_code=500, detail="Error interno procesando el archivo PDF.") from exc
        finally:
            await file.close()

    payload_text = "\n\n".join(merged_texts).strip()
    if not payload_text:
        raise HTTPException(status_code=400, detail="No se pudo extraer texto util del contenido recibido.")

    payload = {"provider_name": provider_name.strip() or "proveedor_sin_nombre", "text": payload_text}
    command = f"{UPLOAD_PREFIX}{json.dumps(payload, ensure_ascii=False)}"
    graph_app = request.app.state.graph
    try:
        state = invoke_graph(graph_app, thread_id, command)
        parsed = SessionStateModel.model_validate(state)
    except Exception as exc:
        logger.exception("Error incorporando contenido en sesion desde /upload", exc_info=exc)
        raise HTTPException(status_code=500, detail="Error interno incorporando el contenido a la sesion.") from exc

    logger.info(
        "Respuesta /upload thread_id=%s estado=%s extracted_chars=%d pending_inputs=%d",
        thread_id,
        parsed.estado,
        len(payload_text),
        len(parsed.pending_inputs),
    )

    return {
        "status": "ok",
        "message": "Contenido incorporado a la sesion.",
        "estado": parsed.estado,
        "pending_inputs": len(parsed.pending_inputs),
        "providers_detected": [provider.nombre for provider in parsed.proveedores],
        "extracted_chars": len(payload_text),
    }
