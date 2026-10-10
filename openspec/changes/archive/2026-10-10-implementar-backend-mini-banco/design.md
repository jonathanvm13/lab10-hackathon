# Design

## Context

No hay paquete Python, `pyproject.toml` ni pruebas. El contrato está en `docs/standards/openapi.yml` y el diseño de componentes en `docs/architecture/arquitectura.md` y `docs/architecture/doc-diseno.md` §3. La motivación está en `proposal.md`. El comportamiento exigible está en `specs/mini-banco/spec.md`.

Las reglas de librerías, capas, auth, errores, logging, tipado, pruebas y calidad se aplican tal como están en `docs/standards/backend-standards.md` y `docs/standards/documentation-standards.md`. Este diseño no las reescribe.

El log `docs/architecture/experimentos.jsonl` es el oráculo de los casos grabados. `herramientas/ctl.py` ya calcula el mismo control ISO 7064 que el contrato; el paquete desplegable no importa esa carpeta.

## Goals / Non-Goals

**Goals:**

- Un proceso determinista cuyo entrypoint es `app.entrada:app`.
- El primer fallo del pipeline responde un ejemplo del contrato.
- Pruebas unitarias por módulo y un replay en proceso del log (salvo `c2`), con cada paso bajo 5 segundos.
- El `README.md` de la raíz basta para instalar, probar y levantar el servicio. El código se explica solo: el README no repite reglas de negocio ni el contrato.
- `railway.toml` en la raíz deja el servicio listo para Railway: una réplica, sin solape y sin el token en el repo.

**Non-Goals:**

- Reimplementar `herramientas/` ni un `replay.py` que llame a un host externo.
- Confirmar un `HALT` real o persistir el estado si el proceso muere.
- Cambiar `docs/standards/openapi.yml`.

## Decisions

### 1. Paquete `app` con un módulo por componente

El diseño original guarda el clon en `clon/`. El equipo pidió `app`. Los estándares piden un archivo de pruebas por módulo, así que no es un solo `app.py`.

| Módulo | Responsabilidad |
|---|---|
| `app/entrada.py` | `crear_app(configuracion)`, ruta comodín, handlers y `app` de producción |
| `app/configuracion.py` | Token, nivel de log, orden del pipeline y parámetros del control |
| `app/catalogo.py` | `CodigoError`, cuerpos y status copiados de los ejemplos |
| `app/errores.py` | `ErrorDominio` |
| `app/pipeline.py` | Recorre el orden y se detiene en el primer `ErrorDominio` |
| `app/control.py` | ISO 7064 MOD 97-10 y comparación textual |
| `app/estado.py` | Cuentas, saldos, operaciones, strikes y correlativos |
| `app/motor.py` | PING, ALTA, CONSULTA, DEPOSITO, TRANSFER, ANULA, HALT |
| `app/registro.py` | JSON a stdout y redacción del token |

Alternativa descartada: un único archivo. Incumple el estándar de pruebas por módulo y mezcla el catálogo con el estado.

`crear_app` recibe la configuración para que las fixtures inyecten un token falso. La instancia de producción lee `APP_AUTH_TOKEN` y no arranca si falta o está vacía. FastAPI se construye como exige el estándar (`docs_url`, `redoc_url`, `openapi_url` en `None`, `redirect_slashes=False`). El cuerpo se lee con `await request.body()` y `json.loads`. Nadie arma `JSONResponse` fuera de la entrada y el catálogo.

### 2. El catálogo se copia; no se lee el YAML en runtime

`pyyaml` es dependencia de desarrollo. El paquete desplegable no abre `docs/standards/openapi.yml` ni hace red. Los textos (incluido `recieved` y el espacio final de E301) viven en `app/catalogo.py`. La prueba de contrato compara cada cuerpo con `components.examples`.

Alternativa descartada: cargar el YAML al arrancar. Metería un archivo de docs en el camino de producción y una dependencia que el estándar deja en dev.

### 3. Estado en un objeto del proceso

`Estado` vive en `app.state`. Un solo proceso, un solo objeto. `reset()` vacía cuentas, operaciones y strikes y devuelve los correlativos a `0001`. La fixture `estado_limpio` lo llama antes de cada test.

`ANULA` no emite un `OP` nuevo. Un depósito suma y su anulación resta ese monto (el saldo puede quedar negativo, log `x12` id 873). Una transferencia resta al origen y suma al destino; anularla invierte esos dos movimientos. La segunda anulación no mueve saldos. Un id que no es una operación existente (`OP-1`, `xyz`, un id nunca emitido) es `E402`.

Los strikes son un contador por cuenta origen, con las reglas de la spec. `HALT` lanza `E520` y no toca el estado ni el proceso.

Alternativa descartada: SQLite. El diseño ya la descartó: cada evaluación empieza con `/__reset`.

### 4. Pipeline configurable, monto explícito

El orden es una lista en `configuracion.py`, la misma de la spec. `PING` salta las dos comprobaciones de control y, si trae más de un argumento, cae en aridad.

Monto válido: entero decimal sin signo ni ceros a la izquierda, de 1 a 10 dígitos. Sale del barrido del log (`x3`/`x4`: `1000000000` aceptado, `10281249999` rechazado; `0`, `001`, negativos y decimales rechazados). `E303` va antes de `E304` y de `E401`. El tope de `TRANSFER` es `100000` inclusive (`s1` id 11 acepta `100000`; id 10 rechaza `120000` con `E506`).

No hay código de error para “demasiadas cuentas”. El supuesto S7 del diseño sigue sin un tope observado; no se inventa uno.

### 5. Pruebas

| Capa | Dónde | Qué cubre |
|---|---|---|
| Unitarias | `pruebas/unitarias/test_<modulo>.py` | Una unidad por test: control, catálogo, estado, motor, pipeline, registro, entrada |
| Contrato | `pruebas/contrato/` | OpenAPI válido, versión `1.0.0`, catálogo igual a los ejemplos, y replay del jsonl |
| Seguridad | marca `security` | Auth, logs sin token, sin clientes de red en el paquete |

El replay usa `TestClient` contra `crear_app` y es la medición de este cambio: corre con la suite, antes del deploy, y falla si un paso tarda 5 segundos o más. No se agrega `herramientas/replay.py` ni se llama a un host. Los 20 ejemplos oficiales ya están en la secuencia `s1` del log.

Interpreta cada línea como la spec de replay: sin prefijo es `POST /msg` con el token de prueba; el prefijo `[MÉTODO RUTA resto]` fija método, ruta y auth, en el orden de coincidencia de esa spec. Un objeto se manda como JSON, `"-"` no manda cuerpo y el resto del texto se manda tal cual. Se omite solo `c2`. Cada secuencia incluida arranca en estado limpio, también `adv-a1`–`adv-a6` y las cinco `humo-*` que no traen reset. JSON se compara como objeto; si no es JSON, como texto.

Cobertura de ramas del paquete `app` ≥ 90 %, más la tabla de calidad del estándar antes de dar por cerrado el cambio.

### 6. Railway con `railway.toml`

El archivo vive en la raíz y fija build y arranque. No sustituye las variables del servicio: `APP_AUTH_TOKEN` (obligatoria) y `APP_LOG_LEVEL` (opcional) se cargan en el panel de Railway.

| Campo | Valor | Por qué |
|---|---|---|
| `build.builder` | `RAILPACK` | Builder por defecto de Railway; lee `pyproject.toml` y el lockfile |
| `build.buildCommand` | `uv sync --frozen --no-dev` | El mismo install de deploy del estándar |
| `deploy.startCommand` | uvicorn en `0.0.0.0`, puerto `$PORT`, `--workers 1`, `--no-access-log` | Una sola instancia; Railway inyecta `PORT` |
| `deploy.numReplicas` | `1` | El estado es memoria del proceso |
| `deploy.overlapSeconds` | `0` | Dos procesos a la vez partirían el estado durante el deploy |
| `deploy.sleepApplication` | `false` | La evaluación no puede encontrar el servicio dormido |
| `deploy.restartPolicyType` | `ON_FAILURE` | Reinicia si el proceso muere; no es autoescalado |
| `healthcheckPath` | ausente | `GET /health` responde 401 sin `Authorization`; el chequeo de Railway no manda ese header |

Alternativa descartada: healthcheck en `/health`. El deploy quedaría unhealthy.

## Risks / Trade-offs

- [El tope de 10 dígitos del monto está inferido del barrido, no de una frase del contrato] → El replay del log lo confirma; si una línea discrepa, se corrige el validador, no el contrato.
- [S7: no se exploró un tope de cuentas] → No se añade un error nuevo. El replay no puede demostrar un tope que el log no contiene.
- [FastAPI responde 404/405/422 por su cuenta] → Ruta comodín y handlers del estándar. Hay tests de `HEAD`, métodos no soportados y `500`.
- [El replay acopla la suite a un log grande] → Corre en proceso, sin red. Una seq sin reset (`c2`) se excluye para no mezclar estado.
- [`clon/` y `app/` son dos nombres para el mismo despliegue] → Railway arranca `app.entrada:app`. `herramientas/` queda fuera del paquete.
- [Railway deja de leer `railway.toml` el 2026-12-01 y un servicio nuevo puede ignorarlo] → El archivo queda en la raíz, como pidió el equipo. Si el panel no lo aplica, se copian build, arranque y réplicas al servicio.

## Migration Plan

No hay estado previo que migrar.

1. Añadir `pyproject.toml`, lockfile, `CHANGELOG.md` en `1.0.0` (igual que `info.version`) y el paquete `app`.
2. Correr la tabla de calidad del estándar.
3. Desplegar con `railway.toml`: una réplica, sin solape. Definir `APP_AUTH_TOKEN` en las variables del servicio, no en el archivo.

Rollback: no hay versión anterior en este repo. Si el replay falla, no se despliega.

## Open Questions

Ninguna. Las reglas que cambiarían la spec o las tareas ya están cerradas con el contrato y el log.
