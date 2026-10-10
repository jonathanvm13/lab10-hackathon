# Estándares de backend

> Alcance: el código desplegable (el paquete desplegable) y sus pruebas. `herramientas/` contiene scripts locales y queda fuera de estas reglas.
> El contrato del API está en `docs/standards/openapi.yml`; las reglas de documentación, en `docs/standards/documentation-standards.md`.

## 0. Principios no negociables

| # | Regla |
|---|---|
| P1 | Toda respuesta (OK o error) sale de un **catálogo único** con status y cuerpo exactos, alineado con `docs/standards/openapi.yml` |
| P2 | El orden de validación vive en la configuración y gana el primer fallo |
| P3 | El servicio es determinista y no hace llamadas de red salientes |
| P4 | El estado vive en memoria del proceso; se despliega **1 instancia**, sin autoescalado |
| P5 | El paquete desplegable no contiene código que llame a hosts externos |
| P6 | El token nunca se registra ni se imprime |
| P7 | Excepción inesperada → `500` `text/plain` `Internal Server Error` |

## 1. Librerías y versiones

Verificadas en PyPI (`https://pypi.org/pypi/<paquete>/json`, campo `info.version`) el **2026-10-10**. Se fijan exactas en la configuración del proyecto de uv (`==`) y las transitivas en **el lockfile de uv** (se versiona; el deploy usa `uv sync --frozen --no-dev`).

### 1.1 Runtime (`[project.dependencies]`)

| Paquete | Versión | Publicada | Uso |
|---|---|---|---|
| `fastapi` | `0.143.0` | 2026-10-08 | Framework |
| `uvicorn` | `0.54.0` | 2026-09-25 | Servidor ASGI. Sin extra `[standard]` (no hace falta uvloop/httptools) |

Transitivas relevantes (fijadas por el lockfile de uv, no se declaran): `starlette 1.7.0`, `pydantic 2.14.0` (versiones actuales en PyPI a la fecha; `uv lock` resuelve las compatibles con fastapi).

### 1.2 Desarrollo (`[dependency-groups] dev`)

| Paquete | Versión | Publicada | Uso |
|---|---|---|---|
| `pytest` | `9.1.1` | 2026-06-19 | Tests |
| `pytest-cov` | `7.1.0` | 2026-03-21 | Cobertura |
| `httpx` | `0.28.1` | 2024-12-06 | Requerido por `fastapi.testclient.TestClient` |
| `ruff` | `0.17.0` | 2026-10-09 | Lint + formato |
| `mypy` | `2.4.0` | 2026-10-01 | Tipado estricto |
| `bandit` | `1.9.4` | 2026-02-25 | SAST del código |
| `pip-audit` | `2.10.1` | 2026-06-10 | CVEs de dependencias |
| `openapi-spec-validator` | `0.9.0` | 2026-05-20 | Validar `docs/standards/openapi.yml` (OpenAPI 3.1) en tests de contrato |
| `pyyaml` | `6.0.3` | 2025-09-25 | Leer `docs/standards/openapi.yml` en tests |
| `types-PyYAML` | `6.0.12.20260906` | 2026-09-06 | Stubs para `mypy --strict` |

Notas:
- `httpx 0.28.1` es la última estable aunque tenga casi 2 años: es correcto, no un error.
- `fastapi 0.143.0` es muy reciente. Si `uv lock` o los tests fallan, se baja a la versión anterior y se anota en el changelog del proyecto.
- Todas declaran `requires_python` compatible con **3.13**. El proyecto fija `requires-python = ">=3.13,<3.14"`.

Configuración de ejemplo para la sección de proyecto y dependencias de uv:

```toml
[project]
name = "<paquete>"
version = "1.0.0"
requires-python = ">=3.13,<3.14"
dependencies = ["fastapi==0.143.0", "uvicorn==0.54.0"]

[dependency-groups]
dev = [
  "pytest==9.1.1", "pytest-cov==7.1.0", "httpx==0.28.1",
  "ruff==0.17.0", "mypy==2.4.0", "bandit==1.9.4", "pip-audit==2.10.1",
  "openapi-spec-validator==0.9.0", "pyyaml==6.0.3", "types-PyYAML==6.0.12.20260906",
]
```

| Acción | Comando |
|---|---|
| Instalar (dev) | `uv sync --frozen` |
| Agregar dep | `uv add <pkg>==<ver>` / `uv add --group dev <pkg>==<ver>` |
| Actualizar lock | `uv lock --upgrade-package <pkg>` (nunca `--upgrade` global antes de un deploy) |
| Deploy | `uv sync --frozen --no-dev` + `uv run uvicorn <paquete>.<entrypoint>:app --host 0.0.0.0 --port $PORT --workers 1 --no-access-log` |

## 2. Versionamiento del API

| Regla | Detalle |
|---|---|
| v1 implícita | Las rutas de v1 van **sin** prefijo de versión (no se agrega `/v1`) |
| v2 explícita | Una versión nueva en paralelo vive en `/v2/...`; v1 sigue intacta sin prefijo |
| Versión del contrato | SemVer en `info.version` de `docs/standards/openapi.yml` = `version` de la configuración del proyecto de uv |
| Registro | Cada cambio de versión tiene entrada en el changelog del proyecto ([Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); ver `docs/standards/documentation-standards.md` §5) |
| MAJOR | Solo cuando se expone una ruta nueva (`/v2/...`) |
| MINOR | Cambio de comportamiento compatible en las rutas existentes |
| PATCH | Correcciones para cumplir el contrato ya documentado |

## 3. Autorización

| Regla | Detalle |
|---|---|
| Header | `Authorization: Bearer <token>`; esquema `Bearer` exacto, **sensible a mayúsculas**, un espacio |
| Token | Variable de entorno **`APP_AUTH_TOKEN`** |
| Arranque | Si `APP_AUTH_TOKEN` falta o está vacía, el proceso **no arranca** (fail-fast) |
| Comparación | En tiempo constante: `hmac.compare_digest(header.encode("utf-8"), f"Bearer {token}".encode("utf-8"))`. Se comparan **bytes**: con `str` no ASCII `compare_digest` lanza `TypeError` y daría 500 |
| Fallo | Sin header, token inválido, sin `Bearer`, `Bearer` sin token o `bearer` en minúscula → respuesta de no autorizado del catálogo (401) |
| Orden | 1) ruta + método; 2) auth; 3) resto del pipeline |
| Alcance | Aplica a todas las rutas del servicio |
| Exposición del token | Nunca en código, tests (usar un token falso fijo definido en las fixtures compartidas de pruebas), logs ni mensajes de error |

## 4. Manejo de errores

### 4.1 Reglas

| # | Regla |
|---|---|
| E1 | Todas las respuestas salen del catálogo de respuestas con un sobre de error uniforme: `{"error":"E000","mensaje":"..."}` (+ campos extra solo donde el contrato los define). Los textos se copian literalmente de `docs/standards/openapi.yml`, incluidos espacios y erratas que formen parte del contrato |
| E2 | El dominio lanza excepciones tipadas (`ErrorDominio(codigo)`); un único handler las traduce con el catálogo. Nadie construye `JSONResponse` a mano fuera del entrypoint y el catálogo de respuestas |
| E3 | `CodigoError` es un `StrEnum`; el catálogo es `Mapping[CodigoError, Respuesta]` y un test verifica que cubre todo el enum |
| E4 | Serialización: `JSONResponse` de Starlette (`ensure_ascii=False`, sin espacios) |
| E5 | El cuerpo se lee con `await request.body()` y `json.loads` propio: **no** se usan modelos Pydantic ni parámetros declarados (evita los 422 de FastAPI). Con claves duplicadas, `json.loads` conserva la última |
| E6 | `except Exception` solo en el handler global; prohibido silenciar excepciones en el dominio |

### 4.2 Configuración de FastAPI y handlers

Los handlers globales reemplazan las respuestas por defecto del framework (404, 405, 422).

| Configuración / handler | Valor / respuesta | Por qué |
|---|---|---|
| `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)` | — | `/docs`, `/redoc` y `/openapi.json` responden como cualquier ruta inexistente; el contrato se publica en `docs/standards/openapi.yml` |
| `redirect_slashes=False` | — | Una ruta con barra final es una ruta desconocida, no un 307 |
| Ruta comodín `/{ruta:path}` con **todos** los métodos | Despacha a mano | Evita el 405 de Starlette y el 404 `{"detail":...}` |
| Handler `StarletteHTTPException` (404/405) | Respuesta de ruta desconocida del catálogo | Por si algo escapa a la ruta comodín |
| Handler `RequestValidationError` (422) | `500` texto plano + log ERROR | No debería ocurrir (E5); si ocurre es un bug |
| Handler `ErrorDominio` | Catálogo | E2 |
| Handler `Exception` | `PlainTextResponse("Internal Server Error", status_code=500)` + log ERROR con traceback | P7 |
| `HEAD` en cualquier ruta | `Response(status_code=404)`, **cuerpo vacío** | Respuesta explícita |
| Sin middleware CORS | — | `OPTIONS` se trata como método no soportado |

## 5. Logging

| Aspecto | Estándar |
|---|---|
| Librería | `logging` estándar + `JsonFormatter` propio en el módulo de logging (sin dependencias extra) |
| Destino | `stdout`, una línea JSON por registro |
| Nivel | Variable de entorno **`APP_LOG_LEVEL`** (default `INFO`) |
| Uvicorn | `--no-access-log` (la app emite su propio log por request) |
| Uso | Depuración. No son métricas ni auditoría |

Campos por request (nivel INFO):

| Campo | Ejemplo | Nota |
|---|---|---|
| `ts` | `2026-10-10T18:00:00.123Z` | UTC ISO 8601 |
| `nivel` | `INFO` | |
| `metodo` | `POST` | |
| `ruta` | `/recurso` | Sin query string |
| `status` | `400` | |
| `codigo` | `E000` / `null` | Código del catálogo |
| `paso` | `validacion_formato` / `null` | Paso del pipeline que falló |
| `duracion_ms` | `1.42` | |
| `cuerpo` | `"..."` | Contenido relevante del cuerpo, truncado a 500 caracteres |

| Regla | Detalle |
|---|---|
| Excepción | `logger.exception(...)` → nivel ERROR con `traceback` en el JSON |
| Redacción | Nunca se loguean headers. `FiltroRedaccion` reemplaza cualquier ocurrencia del token y el patrón `Bearer \S+` por `Bearer ***` en mensaje y campos |
| Prohibido | `print()` en el paquete desplegable (ruff `T20`) |

## 6. Tipado y estilo

| Herramienta | Regla |
|---|---|
| ruff | Lint + formato. `pydocstyle convention = "google"` |
| mypy | `--strict` sobre el paquete desplegable y las pruebas |
| Idioma | Identificadores en español sin tildes (`respuesta`, `configuracion`); ver `docs/standards/documentation-standards.md` §3 |
| Tipos | Sin `Any` explícito en el paquete desplegable; `dataclass(slots=True, frozen=True)` para valores; `Final` para constantes; `StrEnum` para códigos |

Configuración de ejemplo para la sección de herramientas de uv (ruff y mypy):

```toml
[tool.ruff]
target-version = "py313"
line-length = 100
src = ["<paquete>", "<carpeta_de_pruebas>"]
extend-exclude = ["herramientas"]   # scripts locales, fuera de las reglas del paquete desplegable

[tool.ruff.lint]
select = [
  "E", "W", "F",   # pycodestyle, pyflakes
  "I",             # isort
  "N",             # pep8-naming
  "UP",            # pyupgrade
  "B",             # bugbear
  "S",             # bandit (rápido, en cada lint)
  "BLE",           # blind except
  "A",             # builtins sombreados
  "C4", "SIM", "RET", "PIE",
  "T20",           # sin print
  "DTZ",           # datetimes con tz
  "PTH",           # pathlib
  "ARG", "ERA",    # args sin uso, código comentado
  "PL",            # pylint
  "TRY",           # buenas prácticas de excepciones
  "ANN",           # anotaciones
  "D",             # pydocstyle
  "RUF",
]
ignore = ["TRY003"]  # mensajes de excepción cortos son aceptables

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"<carpeta_de_pruebas>/**" = ["S101", "D", "ANN", "PLR2004", "ARG001"]

[tool.ruff.format]
quote-style = "double"
docstring-code-format = true

[tool.mypy]
python_version = "3.13"
strict = true
warn_unreachable = true
files = ["<paquete>", "<carpeta_de_pruebas>"]
```

## 7. Pruebas unitarias y de contrato

| Aspecto | Estándar |
|---|---|
| Framework | `pytest` + `fastapi.testclient.TestClient` (httpx) |
| Pruebas unitarias | Una unidad aislada por test; un archivo de pruebas por módulo del paquete desplegable; las del entrypoint cubren rutas, métodos, `HEAD`, 500 y handlers |
| Pruebas de contrato | Validación de `docs/standards/openapi.yml` y comparación de respuestas contra casos grabados (pares request → respuesta esperada), ejecutados en proceso y con estado reiniciado al inicio |
| Nombres | `test_<unidad>_<escenario>_<resultado>`, p. ej. `test_auth_bearer_minuscula_responde_401`, `test_catalogo_cubre_todo_el_enum_pasa` |
| Patrón | Arrange-Act-Assert, separados por una línea en blanco; un comportamiento por test |
| Fixtures | `token_prueba` (valor falso fijo), `app` (vía `crear_app(settings)` para inyectar config), `client` (TestClient con header), `estado_limpio` (autouse: `reset()` del estado en memoria); viven en las fixtures compartidas de pruebas |
| Parametrizar | `@pytest.mark.parametrize(..., ids=...)` para tablas de casos |
| Fuente | Los casos de reglas no obvias citan su origen (ticket, spec o caso grabado) en `ids=[...]` o en un comentario |
| Comparación | JSON → igualdad de objetos; no JSON → texto exacto |
| Cobertura | **≥ 90 %** del paquete desplegable con ramas (`--cov-fail-under=90`) |

Configuración de ejemplo para la sección de herramientas de uv (pytest y coverage):

```toml
[tool.pytest.ini_options]
testpaths = ["<carpeta_de_pruebas>"]
addopts = "-ra --strict-markers --strict-config"
xfail_strict = true
markers = ["security: tests de seguridad"]

[tool.coverage.run]
source = ["<paquete>"]
branch = true

[tool.coverage.report]
show_missing = true
fail_under = 90
```

| Objetivo | Comando |
|---|---|
| Todo + cobertura | `uv run pytest --cov=<paquete> --cov-branch --cov-report=term-missing --cov-fail-under=90` |
| Solo unitarias | `uv run pytest <carpeta_de_pruebas_unitarias>` |
| Solo contrato | `uv run pytest <carpeta_de_pruebas_de_contrato>` |
| Solo seguridad | `uv run pytest -m security` |
| Un test | `uv run pytest -k test_auth_bearer_minuscula_responde_401` |

## 8. Pruebas de seguridad

### 8.1 bandit (código)

| | |
|---|---|
| Comando | `uv run bandit -c <configuracion_del_proyecto_uv> -r <paquete>` |
| Config | Configuración de ejemplo para la sección de herramientas de uv: `[tool.bandit]` `exclude_dirs = ["<carpeta_de_pruebas>", "herramientas"]` |
| Criterio | 0 alertas de severidad MEDIUM o HIGH |
| Ante una alerta | 1) corregir; 2) si es falso positivo, `# nosec BXXX  # motivo` en la línea (nunca `# nosec` sin código ni motivo) y anotarlo en el PR |

### 8.2 pip-audit (dependencias)

| | |
|---|---|
| Comando | `uv export --frozen --format requirements-txt --no-hashes --no-emit-project -o "$TMPDIR/<requisitos_exportados>"` y luego `uv run pip-audit --strict --no-deps --disable-pip -r "$TMPDIR/<requisitos_exportados>"` |
| Criterio | 0 vulnerabilidades conocidas (runtime y dev) |
| Ante una alerta | 1) `uv lock --upgrade-package <pkg>` a la versión corregida; 2) correr toda la tabla §9; 3) si no hay fix y el paquete es solo dev o el código vulnerable no se usa, `--ignore-vuln <ID>` con motivo en el changelog del proyecto; 4) si es runtime y explotable, no se despliega |

### 8.3 Tests pytest de seguridad (marca `security`)

Son pruebas unitarias con `@pytest.mark.security`. La marca se registra en la sección de herramientas de uv: `[tool.pytest.ini_options] markers = ["security: tests de seguridad"]`.

| Prueba | Qué verifica |
|---|---|
| Autorización | Todas las variantes de header inválido → 401 en todas las rutas; la ruta desconocida se resuelve antes que la auth; un token con caracteres no ASCII → 401 y **no** 500 |
| Logs sin token | Con `caplog`/`capsys`, tras requests con token válido, inválido y con el token dentro del cuerpo, ni el token ni `Authorization` aparecen en la salida; tras una excepción forzada, tampoco en el traceback |
| Sin llamadas externas | Recorre todos los módulos del paquete desplegable y falla si encuentra URLs `http://`/`https://` o imports de clientes de red (`httpx`, `requests`, `urllib.request`, `http.client`, `socket`, `aiohttp`) no previstos. Además, `[project.dependencies]` no incluye clientes HTTP |

## 9. Comandos de calidad (antes de cada deploy)

Se corren en este orden; cualquier fallo detiene el deploy.

| # | Paso | Comando | Criterio |
|---|---|---|---|
| 1 | Formato | `uv run ruff format --check .` | Sin cambios pendientes |
| 2 | Lint | `uv run ruff check .` | 0 errores |
| 3 | Tipos | `uv run mypy` | 0 errores (`strict`) |
| 4 | Tests + cobertura | `uv run pytest --cov=<paquete> --cov-branch --cov-fail-under=90` | Todo verde, ≥ 90 % |
| 5 | SAST | `uv run bandit -c <configuracion_del_proyecto_uv> -r <paquete>` | 0 MEDIUM/HIGH |
| 6 | Dependencias | `uv export … -o "$TMPDIR/<requisitos_exportados>" && uv run pip-audit --strict --no-deps --disable-pip -r "$TMPDIR/<requisitos_exportados>"` | 0 vulnerabilidades |
