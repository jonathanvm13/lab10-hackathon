"""Pruebas de contrato de `railway.toml`."""

import re
import tomllib
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[2]
_ARRANQUE = "uv run uvicorn app.entrada:app --host 0.0.0.0 --port $PORT --workers 1 --no-access-log"


def _texto() -> str:
    return (_RAIZ / "railway.toml").read_text(encoding="utf-8")


def _secciones() -> tuple[dict[str, object], dict[str, object]]:
    cargado = tomllib.loads(_texto())
    deploy = cargado["deploy"]
    build = cargado["build"]
    assert isinstance(deploy, dict)
    assert isinstance(build, dict)
    return build, deploy


def test_railway_una_sola_instancia() -> None:
    build, deploy = _secciones()

    assert build["builder"] == "RAILPACK"
    assert build["buildCommand"] == "uv sync --frozen --no-dev"
    assert deploy["startCommand"] == _ARRANQUE
    assert deploy["numReplicas"] == 1
    assert deploy["overlapSeconds"] == 0
    assert deploy["sleepApplication"] is False
    assert "--workers 1" in str(deploy["startCommand"])
    assert "$PORT" in str(deploy["startCommand"])


def test_railway_sin_secreto_ni_asignacion_de_token() -> None:
    texto = _texto()

    assert re.search(r"APP_AUTH_TOKEN\s*=", texto) is None
    assert "Bearer " not in texto


def test_railway_sin_healthcheck_anonimo() -> None:
    assert "healthcheckPath" not in _texto()
