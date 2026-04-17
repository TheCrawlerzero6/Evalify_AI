from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.routes as app_routes


def _provider(nombre: str) -> dict[str, Any]:
    return {
        "nombre": nombre,
        "texto_original": "texto base",
        "busqueda_web": {},
        "fuentes_web": {},
        "analisis_individual": {},
    }


def _state(**overrides: Any) -> dict[str, Any]:
    base = {
        "input": "",
        "output": "ok",
        "estado": "ingesta",
        "criterios": [],
        "proveedores": [],
        "resultado_final": None,
        "pending_inputs": [],
    }
    base.update(overrides)
    return base


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.state.graph = object()
    app.include_router(app_routes.router)
    return TestClient(app)


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_invoke_graph(_app: object, thread_id: str, message: str) -> dict[str, Any]:
        assert thread_id == "th-1"
        assert message == "hola"
        return _state(
            output="respuesta",
            estado="comparacion",
            criterios=["precio"],
            proveedores=[_provider("Proveedor A")],
        )

    monkeypatch.setattr(app_routes, "invoke_graph", _fake_invoke_graph)

    response = client.post("/chat", json={"thread_id": "th-1", "message": "hola"})

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "respuesta"
    assert data["estado"] == "comparacion"
    assert data["criterios"] == ["precio"]
    assert data["proveedores"] == ["Proveedor A"]


def test_chat_internal_error_returns_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _broken_invoke_graph(_app: object, _thread_id: str, _message: str) -> dict[str, Any]:
        raise RuntimeError("error interno")

    monkeypatch.setattr(app_routes, "invoke_graph", _broken_invoke_graph)

    response = client.post("/chat", json={"thread_id": "th-err", "message": "hola"})

    assert response.status_code == 500
    assert response.json()["detail"] == "Error interno procesando la solicitud de chat."


def test_session_state_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_get_session_state(_app: object, thread_id: str) -> dict[str, Any]:
        assert thread_id == "th-session"
        return _state(estado="fin", output="listo", proveedores=[_provider("Proveedor X")])

    monkeypatch.setattr(app_routes, "get_session_state", _fake_get_session_state)

    response = client.get("/session/th-session")

    assert response.status_code == 200
    data = response.json()
    assert data["estado"] == "fin"
    assert data["output"] == "listo"
    assert len(data["proveedores"]) == 1


def test_upload_requires_text_or_file(client: TestClient) -> None:
    response = client.post("/upload", data={"thread_id": "th-upload"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Debes enviar al menos text o file."


def test_upload_text_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_invoke_graph(_app: object, thread_id: str, _message: str) -> dict[str, Any]:
        assert thread_id == "th-upload-ok"
        return _state(
            estado="ingesta",
            pending_inputs=[{"nombre": "Proveedor X", "texto": "contenido"}],
            proveedores=[],
        )

    monkeypatch.setattr(app_routes, "invoke_graph", _fake_invoke_graph)

    response = client.post(
        "/upload",
        data={"thread_id": "th-upload-ok", "provider_name": "Proveedor X", "text": "Documento base"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["estado"] == "ingesta"
    assert data["pending_inputs"] == 1
    assert data["extracted_chars"] == len("Documento base")


def test_upload_rejects_non_pdf_file(client: TestClient) -> None:
    response = client.post(
        "/upload",
        data={"thread_id": "th-file", "provider_name": "Proveedor Y"},
        files={"file": ("archivo.txt", b"contenido", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Solo se admite PDF en el campo file."


def test_upload_invalid_pdf_returns_400(client: TestClient) -> None:
    response = client.post(
        "/upload",
        data={"thread_id": "th-bad-pdf", "provider_name": "Proveedor Z"},
        files={"file": ("bad.pdf", b"not-a-pdf", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "El archivo PDF es invalido o esta corrupto."


def test_upload_invoke_graph_error_returns_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _broken_invoke_graph(_app: object, _thread_id: str, _message: str) -> dict[str, Any]:
        raise RuntimeError("fallo")

    monkeypatch.setattr(app_routes, "invoke_graph", _broken_invoke_graph)

    response = client.post(
        "/upload",
        data={"thread_id": "th-upload-err", "provider_name": "Proveedor W", "text": "contenido"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Error interno incorporando el contenido a la sesion."
