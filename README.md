# Mini banco

Servicio HTTP. Requiere Python 3.13 y [uv](https://docs.astral.sh/uv/).

## Instalación

```bash
uv sync --frozen
```

## Configuración

Definí el token antes de levantar el proceso. Si falta o está vacío, no arranca.

```bash
export APP_AUTH_TOKEN="cambia-este-token"
```

`APP_LOG_LEVEL` es opcional. El valor por defecto es `INFO`.

## Pruebas

```bash
uv run pytest --cov=app --cov-branch --cov-fail-under=90
```

## Servidor

```bash
uv run uvicorn app.entrada:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --no-access-log
```

## Despliegue

Railway usa `railway.toml` en la raíz: Railpack, `uv sync --frozen --no-dev` y una sola réplica. Definí `APP_AUTH_TOKEN` en las variables del servicio. No va en el repositorio.
