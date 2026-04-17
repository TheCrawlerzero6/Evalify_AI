from __future__ import annotations

import logging
import os
from typing import Dict, List

import httpx

from app.config import TAVILY_SEARCH_ENDPOINT
from app.schemas.domain import SourceRef

logger = logging.getLogger(__name__)


def _tavily_search(query: str, max_results: int = 3) -> List[dict]:
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Falta TAVILY_API_KEY en variables de entorno.")

    logger.debug("Consultando Tavily query=%s max_results=%d", query, max_results)

    payload = {
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(timeout=20.0) as client:
        response = client.post(TAVILY_SEARCH_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
    results = data.get("results", [])
    logger.debug("Respuesta Tavily resultados=%d", len(results))
    return results


def _normalize_result(result: dict, criterio: str, categoria: str | None = None) -> SourceRef:
    return SourceRef(
        titulo=result.get("title", ""),
        url=result.get("url", ""),
        snippet=(result.get("content", "") or "").strip(),
        criterio=criterio,
        categoria=categoria,
    )


def search_for_criterion(provider_name: str, criterion: str) -> Dict[str, List]:
    criterion = criterion.lower().strip()
    logger.info("Busqueda por criterio proveedor=%s criterio=%s", provider_name, criterion)
    if criterion == "reputacion":
        queries = {
            "reviews": f"{provider_name} reseñas usuarios opiniones",
            "prensa": f"{provider_name} noticias prensa análisis",
            "foros": f"{provider_name} foro experiencias comentarios",
        }
        observations: List[str] = []
        sources: List[SourceRef] = []
        for category, query in queries.items():
            results = _tavily_search(query=query, max_results=2)
            for item in results:
                ref = _normalize_result(item, criterio="reputacion", categoria=category)
                if not ref.url:
                    continue
                sources.append(ref)
                if ref.snippet:
                    observations.append(f"[{category}] {ref.snippet}")

        if observations:
            deduped_observations: List[str] = []
            seen = set()
            for obs in observations:
                cleaned = obs.strip()
                if not cleaned or cleaned in seen:
                    continue
                seen.add(cleaned)
                deduped_observations.append(cleaned)
            logger.info(
                "Busqueda reputacion completada proveedor=%s observaciones=%d fuentes=%d",
                provider_name,
                len(deduped_observations[:6]),
                len(sources),
            )
            return {"observaciones": deduped_observations[:6], "fuentes": sources}
        logger.info("Busqueda reputacion sin evidencia proveedor=%s", provider_name)
        return {"observaciones": ["Sin evidencia web suficiente para reputación."], "fuentes": []}

    query = f"{provider_name} {criterion}"
    results = _tavily_search(query=query, max_results=3)
    observations = []
    sources: List[SourceRef] = []
    for item in results:
        ref = _normalize_result(item, criterio=criterion)
        if not ref.url:
            continue
        sources.append(ref)
        if ref.snippet:
            observations.append(ref.snippet)

    if not observations:
        observations = [f"Sin evidencia web suficiente para {criterion}."]
    logger.info(
        "Busqueda criterio completada proveedor=%s criterio=%s observaciones=%d fuentes=%d",
        provider_name,
        criterion,
        len(observations),
        len(sources),
    )
    return {"observaciones": observations, "fuentes": sources}
