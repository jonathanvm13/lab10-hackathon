"""Pruebas de contrato de `railpack.json`."""

import json
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[2]
_ARRANQUE = "uv run uvicorn app.entrada:app --host 0.0.0.0 --port $PORT --workers 1 --no-access-log"


def _texto() -> str:
    return (_RAIZ / "railpack.json").read_text(encoding="utf-8")


def _deploy() -> dict[str, object]:
    cargado = json.loads(_texto())
    deploy = cargado["deploy"]
    assert isinstance(deploy, dict)
    return deploy


def test_railpack_arranque() -> None:
    """Railpack lee `railpack.json` (https://railpack.com/config/file)."""
    arranque = _deploy()["startCommand"]

    assert arranque == _ARRANQUE
    assert "--workers 1" in str(arranque)
    assert "$PORT" in str(arranque)


def test_railpack_sin_secreto_ni_asignacion_de_token() -> None:
    texto = _texto()

    assert "APP_AUTH_TOKEN" not in texto
    assert "Bearer " not in texto


def test_railpack_sin_healthcheck_anonimo() -> None:
    assert "healthcheckPath" not in _texto()
