# Mini banco

Servicio HTTP.

## Entorno

Hace falta [uv](https://docs.astral.sh/uv/getting-started/installation/). Python es **3.13**: `pyproject.toml` lo declara con `requires-python = ">=3.13,<3.14"` y `uv.lock` lo fija en `3.13`.

Si `uv --version` no responde:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Si esa misma terminal sigue sin encontrar `uv`, cargá el entorno que dejó el instalador:

```bash
. "$HOME/.local/bin/env"
```

Una terminal nueva ya toma `uv` del perfil del shell.

```bash
uv python install 3.13
```

## Dependencias

| Qué | Dónde |
|---|---|
| Runtime | `pyproject.toml`, sección `[project.dependencies]` |
| Desarrollo y pruebas | `pyproject.toml`, grupo `dev` de `[dependency-groups]` |
| Versiones exactas, incluidas las transitivas | `uv.lock` |

```bash
uv sync --frozen
```

Ese comando crea `.venv` en la raíz e instala el lock, con el grupo `dev`. `uv run` usa ese entorno.

Comprobación:

```bash
uv run python --version
```

La salida tiene que ser Python 3.13.

En el servicio, el mismo lock se instala con `uv sync --frozen --no-dev`.

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

Railway usa Railpack. El arranque está en `railpack.json`. En el servicio dejá una réplica, sin solape y sin dormir la app. Definí `APP_AUTH_TOKEN` en las variables del servicio. No va en el repositorio.
