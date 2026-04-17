from __future__ import annotations

import json
from typing import Dict, List, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.integrations.llm.openai_client import build_llm
from app.integrations.search.tavily_client import search_for_criterion
from app.schemas.domain import (
    CriterioEvaluado,
    ProviderCriterionAssessment,
    ProveedorAnalisis,
    ProveedorInput,
    ResultadoFinal,
    SessionStateModel,
    UserExtraction,
)
from app.services.formatter import format_resultado_final

UPLOAD_PREFIX = "__UPLOAD__::"


class SessionState(TypedDict, total=False):
    input: str
    output: str
    estado: str
    criterios: List[str]
    proveedores: List[dict]
    resultado_final: dict | None
    pending_inputs: List[dict]


def _state_defaults() -> SessionState:
    return SessionStateModel().model_dump()


def _coerce_state(state: SessionState) -> SessionState:
    base = _state_defaults()
    base.update({k: v for k, v in state.items() if v is not None})
    return base


def _normalize_criterios(criteria: List[str]) -> List[str]:
    normalized = []
    seen = set()
    for criterion in criteria:
        value = criterion.strip().lower()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
        if len(normalized) == 3:
            break
    return normalized


def _merge_provider_inputs(existing: List[dict], incoming: List[dict]) -> List[dict]:
    merged: Dict[str, ProveedorAnalisis] = {}
    for provider_dict in existing:
        provider = ProveedorAnalisis.model_validate(provider_dict)
        merged[provider.nombre.strip().lower()] = provider

    for incoming_dict in incoming:
        data = ProveedorInput.model_validate(incoming_dict)
        key = data.nombre.strip().lower()
        if key not in merged:
            merged[key] = ProveedorAnalisis(nombre=data.nombre.strip(), texto_original=data.texto.strip())
            continue
        current = merged[key]
        extra_text = data.texto.strip()
        if extra_text:
            current.texto_original = (current.texto_original + "\n\n" + extra_text).strip()
            merged[key] = current

    return [provider.model_dump() for provider in merged.values()]


def _extract_user_data(message: str) -> UserExtraction:
    llm = build_llm().with_structured_output(UserExtraction)
    prompt = (
        "Extrae datos para comparar proveedores.\n"
        "- proveedores: lista de objetos con nombre y texto\n"
        "- criterios: hasta 3 criterios para comparar\n"
        "- quiere_comparar: true si el usuario pide comparar o cerrar analisis\n"
        "Si no hay datos suficientes devuelve listas vacias."
    )
    try:
        return llm.invoke(
            [
                SystemMessage(content=prompt),
                HumanMessage(content=message),
            ]
        )
    except Exception:
        return UserExtraction()


def _parse_upload_input(message: str) -> ProveedorInput | None:
    if not message.startswith(UPLOAD_PREFIX):
        return None
    payload = message.removeprefix(UPLOAD_PREFIX).strip()
    try:
        data = json.loads(payload)
        return ProveedorInput(
            nombre=data.get("provider_name") or "proveedor_sin_nombre",
            texto=(data.get("text") or "").strip(),
        )
    except Exception:
        return None


def node_ingesta(state: SessionState) -> SessionState:
    current = _coerce_state(state)
    message = (current.get("input") or "").strip()

    upload_payload = _parse_upload_input(message)
    if upload_payload:
        pending = current.get("pending_inputs", [])
        pending.append(upload_payload.model_dump())
        return {
            "pending_inputs": pending,
            "output": "Archivo/texto recibido. Ahora comparte en el chat los nombres de 2 o 3 proveedores y los criterios.",
            "estado": "ingesta",
        }

    extraction = _extract_user_data(message) if message else UserExtraction()
    incoming_inputs = [item.model_dump() for item in extraction.proveedores]
    pending_inputs = current.get("pending_inputs", [])
    all_inputs = pending_inputs + incoming_inputs
    proveedores = _merge_provider_inputs(current.get("proveedores", []), all_inputs)
    criterios = _normalize_criterios(current.get("criterios", []) + extraction.criterios)
    providers_trimmed = False
    if len(proveedores) > 3:
        proveedores = proveedores[:3]
        providers_trimmed = True

    if current.get("estado") == "fin" and not extraction.proveedores and not extraction.criterios:
        resultado = current.get("resultado_final")
        if resultado:
            formatted = format_resultado_final(ResultadoFinal.model_validate(resultado))
            return {"output": formatted, "pending_inputs": []}

    if len(proveedores) < 2:
        base_message = "Necesito al menos 2 proveedores para comparar. Puedes enviar texto directo o usar /upload con PDF."
        if providers_trimmed:
            base_message = "Detecte mas de 3 proveedores y recorte a los primeros 3. " + base_message
        return {
            "proveedores": proveedores,
            "criterios": criterios,
            "pending_inputs": [],
            "estado": "esperando_proveedores",
            "output": base_message,
        }

    if not criterios:
        base_message = "Perfecto. Ahora define hasta 3 criterios (ejemplo: precio, soporte, integraciones)."
        if providers_trimmed:
            base_message = "Detecte mas de 3 proveedores y recorte a los primeros 3. " + base_message
        return {
            "proveedores": proveedores,
            "criterios": [],
            "pending_inputs": [],
            "estado": "criterios",
            "output": base_message,
        }

    base_message = "Datos completos. Iniciando enriquecimiento con busqueda web por criterio y reputacion."
    if providers_trimmed:
        base_message = "Detecte mas de 3 proveedores y recorte a los primeros 3. " + base_message
    return {
        "proveedores": proveedores,
        "criterios": criterios,
        "pending_inputs": [],
        "estado": "enriquecimiento",
        "output": base_message,
    }


def node_definir_criterios(state: SessionState) -> SessionState:
    current = _coerce_state(state)
    if current.get("criterios"):
        return {"estado": "enriquecimiento"}

    extraction = _extract_user_data((current.get("input") or "").strip())
    criterios = _normalize_criterios(extraction.criterios)
    if not criterios:
        return {
            "estado": "esperando_criterios",
            "output": "Aun no detecto criterios validos. Indica hasta 3 (ejemplo: precio, soporte, integraciones).",
        }
    return {"criterios": criterios, "estado": "enriquecimiento"}


def node_enriquecer(state: SessionState) -> SessionState:
    current = _coerce_state(state)
    criterios_base = _normalize_criterios(current.get("criterios", []))
    criterios_total = criterios_base + (["reputacion"] if "reputacion" not in criterios_base else [])
    providers = []

    for provider_dict in current.get("proveedores", []):
        provider = ProveedorAnalisis.model_validate(provider_dict)
        busqueda_web = dict(provider.busqueda_web)
        fuentes_web = dict(provider.fuentes_web)
        for criterio in criterios_total:
            if criterio in busqueda_web and busqueda_web[criterio]:
                continue
            try:
                result = search_for_criterion(provider.nombre, criterio)
                busqueda_web[criterio] = result["observaciones"]
                fuentes_web[criterio] = [source.model_dump() for source in result["fuentes"]]
            except Exception as exc:
                busqueda_web[criterio] = [f"Error consultando web para {criterio}: {exc}"]
                fuentes_web[criterio] = []
        provider.busqueda_web = busqueda_web
        provider.fuentes_web = fuentes_web
        providers.append(provider.model_dump())

    return {
        "proveedores": providers,
        "estado": "analisis",
        "output": "Enriquecimiento completado. Generando analisis individual por proveedor.",
    }


def _analyze_provider(provider: ProveedorAnalisis, criterios: List[str]) -> Dict[str, dict]:
    llm = build_llm().with_structured_output(ProviderCriterionAssessment)
    criterios_total = criterios + (["reputacion"] if "reputacion" not in criterios else [])
    prompt = (
        "Analiza el proveedor SOLO con evidencia disponible.\n"
        "Debes evaluar cada criterio con clasificacion: alto, medio o bajo.\n"
        "Cada evaluacion debe incluir evidencia explicita y origen documento o web.\n"
        "No inventes datos ni fuentes."
    )
    evidence_payload = {
        "criterios": criterios_total,
        "texto_original": provider.texto_original[:12000],
        "busqueda_web": provider.busqueda_web,
    }
    try:
        result = llm.invoke(
            [
                SystemMessage(content=prompt),
                HumanMessage(content=json.dumps(evidence_payload, ensure_ascii=False)),
            ]
        )
        evaluated = {}
        for item in result.evaluaciones:
            crit = item.criterio.strip().lower()
            if crit:
                evaluated[crit] = item.model_dump()
        for crit in criterios_total:
            if crit not in evaluated:
                evaluated[crit] = CriterioEvaluado(
                    criterio=crit,
                    clasificacion="medio",
                    evidencia=f"No hubo evidencia suficiente para {crit}.",
                    origen="web",
                ).model_dump()
        return evaluated
    except Exception as exc:
        return {
            crit: CriterioEvaluado(
                criterio=crit,
                clasificacion="medio",
                evidencia=f"No se pudo evaluar {crit} por error: {exc}",
                origen="web",
            ).model_dump()
            for crit in criterios_total
        }


def node_analisis_individual(state: SessionState) -> SessionState:
    current = _coerce_state(state)
    criterios = _normalize_criterios(current.get("criterios", []))
    providers = []
    for provider_dict in current.get("proveedores", []):
        provider = ProveedorAnalisis.model_validate(provider_dict)
        provider.analisis_individual = _analyze_provider(provider, criterios)
        providers.append(provider.model_dump())
    return {
        "proveedores": providers,
        "estado": "comparacion",
        "output": "Analisis individual finalizado. Generando comparacion consolidada.",
    }


def _build_score_simple(proveedores: List[dict], criterios: List[str]) -> Dict[str, int]:
    score_map = {"alto": 3, "medio": 2, "bajo": 1}
    criterios_total = criterios + (["reputacion"] if "reputacion" not in criterios else [])
    scores: Dict[str, int] = {}
    for provider_dict in proveedores:
        provider = ProveedorAnalisis.model_validate(provider_dict)
        total = 0
        for criterio in criterios_total:
            data = provider.analisis_individual.get(criterio, {})
            total += score_map.get(data.get("clasificacion", "medio"), 2)
        scores[provider.nombre] = total
    return scores


def node_comparacion(state: SessionState) -> SessionState:
    current = _coerce_state(state)
    criterios = _normalize_criterios(current.get("criterios", []))
    providers = current.get("proveedores", [])
    comparison_payload = []
    for provider_dict in providers:
        provider = ProveedorAnalisis.model_validate(provider_dict)
        comparison_payload.append(
            {"nombre": provider.nombre, "analisis_individual": provider.analisis_individual}
        )

    llm = build_llm().with_structured_output(ResultadoFinal)
    prompt = (
        "Genera una comparacion final SOLO con el analisis_individual de cada proveedor.\n"
        "Debes producir: diferencias, similitudes, ventajas, desventajas, conclusion.\n"
        "No incluyas informacion fuera del payload."
    )
    try:
        result = llm.invoke(
            [
                SystemMessage(content=prompt),
                HumanMessage(
                    content=json.dumps({"criterios": criterios, "proveedores": comparison_payload}, ensure_ascii=False)
                ),
            ]
        )
    except Exception:
        result = ResultadoFinal(
            diferencias=["No se pudo inferir diferencias por error de modelo."],
            similitudes=[],
            ventajas=[],
            desventajas=[],
            conclusion="No fue posible concluir automaticamente en este intento.",
        )

    result.score_simple = _build_score_simple(providers, criterios)
    return {
        "resultado_final": result.model_dump(),
        "estado": "fin",
        "output": format_resultado_final(result),
    }


def node_fin(state: SessionState) -> SessionState:
    current = _coerce_state(state)
    resultado = current.get("resultado_final")
    if not resultado:
        return {"output": "No existe un resultado final todavia."}
    return {"output": format_resultado_final(ResultadoFinal.model_validate(resultado))}


def route_after_ingesta(state: SessionState) -> str:
    estado = (state.get("estado") or "").lower()
    if estado == "criterios":
        return "definir_criterios"
    if estado == "enriquecimiento":
        return "enriquecer"
    return END


def route_after_criterios(state: SessionState) -> str:
    if (state.get("estado") or "").lower() == "enriquecimiento":
        return "enriquecer"
    return END


def build_graph(checkpointer=None):
    workflow = StateGraph(SessionState)
    workflow.add_node("ingesta", node_ingesta)
    workflow.add_node("definir_criterios", node_definir_criterios)
    workflow.add_node("enriquecer", node_enriquecer)
    workflow.add_node("analisis_individual", node_analisis_individual)
    workflow.add_node("comparacion", node_comparacion)
    workflow.add_node("fin", node_fin)

    workflow.add_edge(START, "ingesta")
    workflow.add_conditional_edges("ingesta", route_after_ingesta)
    workflow.add_conditional_edges("definir_criterios", route_after_criterios)
    workflow.add_edge("enriquecer", "analisis_individual")
    workflow.add_edge("analisis_individual", "comparacion")
    workflow.add_edge("comparacion", "fin")
    workflow.add_edge("fin", END)

    return workflow.compile(checkpointer=checkpointer)


def invoke_graph(app, thread_id: str, message: str) -> SessionState:
    config = {"configurable": {"thread_id": thread_id}}
    return _coerce_state(app.invoke({"input": message}, config=config))


def get_session_state(app, thread_id: str) -> SessionState:
    snapshot = app.get_state({"configurable": {"thread_id": thread_id}})
    if not snapshot or not getattr(snapshot, "values", None):
        return _coerce_state({})
    return _coerce_state(snapshot.values)
