"""Pruebas de la entrada HTTP."""

import pytest
from app.configuracion import Configuracion
from app.entrada import crear_app
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException
from starlette.responses import Response


def test_entrada_health_y_reset_responden_ok(client: TestClient) -> None:
    health = client.get("/health")
    reinicio = client.post("/__reset")

    assert health.status_code == 200
    assert health.json() == {"ok": True}
    assert reinicio.status_code == 200
    assert reinicio.json() == {"ok": True}


def test_entrada_raiz_responde_e404(client: TestClient) -> None:
    respuesta = client.get("/")

    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "E404"


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("GET", "/msg"),
        ("PUT", "/msg"),
        ("DELETE", "/msg"),
        ("PATCH", "/msg"),
        ("OPTIONS", "/msg"),
        ("POST", "/health"),
        ("GET", "/__reset"),
    ],
)
def test_entrada_metodo_o_ruta_desconocida_responde_e404(
    client: TestClient,
    metodo: str,
    ruta: str,
) -> None:
    respuesta = client.request(metodo, ruta)

    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "E404"


def test_entrada_head_responde_404_con_cuerpo_vacio(client: TestClient) -> None:
    respuesta = client.head("/msg")

    assert respuesta.status_code == 404
    assert respuesta.content == b""


def test_entrada_barra_final_responde_e404(client: TestClient) -> None:
    respuesta = client.post("/msg/", json={"m": "PING;64"})

    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "E404"


def test_entrada_query_string_no_cambia_la_ruta(client: TestClient) -> None:
    respuesta = client.post("/msg?confirm=1", json={"m": "PING;64"})

    assert respuesta.status_code == 200
    assert respuesta.json() == {"pong": True}


def test_entrada_excepcion_responde_500_texto_plano(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(mensaje: str, estado: object = None) -> object:
        raise RuntimeError("falla interna")

    monkeypatch.setattr("app.entrada.procesar", boom)

    respuesta = client.post("/msg", json={"m": "PING;64"})

    assert respuesta.status_code == 500
    assert respuesta.text == "Internal Server Error"
    assert respuesta.headers["content-type"].startswith("text/plain")


def test_entrada_json_lista_responde_e102(client: TestClient) -> None:
    respuesta = client.post("/msg", content=b'["PING;64"]')

    assert respuesta.status_code == 400
    assert respuesta.json()["error"] == "E102"


def test_entrada_json_string_responde_e102(client: TestClient) -> None:
    respuesta = client.post("/msg", content=b'"PING;64"')

    assert respuesta.status_code == 400
    assert respuesta.json()["error"] == "E102"


def test_entrada_sin_token_no_arranca() -> None:
    aplicacion = crear_app(Configuracion(token=""))

    with pytest.raises(RuntimeError, match="APP_AUTH_TOKEN"), TestClient(aplicacion):
        pass


def test_entrada_http_exception_responde_e404(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(_solicitud: Request) -> Response | None:
        raise HTTPException(status_code=405)

    monkeypatch.setattr("app.entrada._paso_ruta", boom)

    respuesta = client.get("/health")

    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "E404"


def test_entrada_validacion_framework_responde_500(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(_solicitud: Request) -> Response | None:
        raise RequestValidationError([])

    monkeypatch.setattr("app.entrada._paso_ruta", boom)

    respuesta = client.get("/health")

    assert respuesta.status_code == 500
    assert respuesta.text == "Internal Server Error"
    assert respuesta.headers["content-type"].startswith("text/plain")
