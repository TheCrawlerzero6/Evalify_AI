from __future__ import annotations

import os
from typing import Dict, List

import httpx

from app.core.config import TAVILY_SEARCH_ENDPOINT
from app.schemas.domain import SourceRef


def _tavily_search(query: str, max_results: int = 3) -> List[dict]:
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Falta TAVILY_API_KEY en variables de entorno.")

    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
    }
    with httpx.Client(timeout=20.0) as client:
        response = client.post(TAVILY_SEARCH_ENDPOINT, json=payload)
        response.raise_for_status()
        data = response.json()
    return data.get("results", [])


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
            summary = " | ".join(observations[:6])
            return {"observaciones": [summary], "fuentes": sources}
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
    return {"observaciones": observations, "fuentes": sources}
