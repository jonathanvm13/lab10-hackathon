# Proposal

## Why

El original desplegó la versión de la tarde en las mismas rutas. El clon y el contrato siguen en la versión de la mañana (`1.0.0`): `saldo` entero, tope de `TRANSFER` en `100000` y `E510` en `409` sin `intentos`. A las 20:00 el clon se evalúa contra esa versión nueva (`docs/architecture/INCIDENT.md`).

## What Changes

- **BREAKING** `CONSULTA` devuelve `saldo` como string: entero interno / 100, dos decimales, sin separador de miles y con `-` si es negativo. Los montos de entrada siguen siendo enteros. Solo `CONSULTA` muestra montos (`docs/architecture/INCIDENT.md`, cambio 1).
- **BREAKING** El tope por operación de `TRANSFER` pasa de `100000` a `50000` inclusive. `50001` responde `E506`. `DEPOSITO` no tiene ese tope. `E506` sigue sumando strike al origen (cambio 2).
- **BREAKING** Una cuenta bloqueada responde `423` con `{"error":"E510","mensaje":"cuenta bloqueada","intentos":N}`. `intentos` cuenta los `TRANSFER` rechazados por bloqueo en ese episodio y vuelve a `1` al bloquear de nuevo tras un desbloqueo. El umbral sigue en 3 strikes; el bloqueo solo aplica como origen; `ANULA` no desbloquea (cambio 3 y reglas reconfirmadas).
- El resto (formato, control, orden de validación, `E301`/sugerencia, `ALTA`, auth y rutas) no cambia.
- Actualizar la documentación del contrato en el mismo cambio: `docs/standards/openapi.yml` (tabla de comandos, patrón y descripción de `saldo`, esquema `423` con `intentos` entero, texto de `POST /__reset`, cuerpos y status) y el changelog bajo `[Unreleased]`, con fuente `docs/architecture/INCIDENT.md`. `info.version`, `pyproject.toml` y `uv.lock` se quedan en `1.0.0`. La frase «v1, sin versión en la ruta» se conserva. En `docs/standards/backend-standards.md` §2 y `docs/standards/documentation-standards.md` §5 se añade la misma excepción, sin quitar MAJOR, MINOR ni PATCH: si el proveedor reemplaza de forma incompatible el contrato en las mismas rutas y el clon debe reflejarlo, se conserva la versión local, se actualiza el contrato y el cambio se anota bajo `[Unreleased]` con la evidencia del incidente. En `docs/architecture/doc-diseno.md` se actualizan el caso C3, la tabla de estado y, en el código, el docstring de `validar_limite`. No se reescriben el conteo de `experimentos.jsonl` en §5.1, los ids `409–557`, `hallazgo.md`, los simulacros, `INCIDENT.md` ni `docs/architecture/plan-incidente.md`: este último es el plan previo al incidente.
- Pruebas en este orden: primero las unitarias nuevas de estos tres comportamientos, y deben fallar contra el código actual; después el contrato, el catálogo y el código; al final la misma suite, ya en verde, más el replay de la versión de la tarde.

Supuesto de versión: no hay salto de versión. El original cambió las mismas rutas y no publicó `/v2`. La excepción nueva de los estándares cubre ese caso y el clon sigue en `1.0.0`.

Supuesto de replay: `docs/architecture/experimentos.jsonl` queda como versión de la mañana y deja de ser el oráculo del servicio vigente. El oráculo pasa a las secuencias desde `humo-1601` en `docs/architecture/incidente-experimentos.jsonl` (ids 93–346). `humo-1534` y `humo-1536` (ids 1–92) siguen siendo la mañana y no se exigen.

## Capabilities

### New Capabilities

- Ninguna.

### Modified Capabilities

- `mini-banco`: formato de `saldo` en `CONSULTA`, tope de `TRANSFER`, respuesta `E510` con `intentos`, y el log que el replay debe reproducir.

## Impact

- Contrato: `docs/standards/openapi.yml` (tabla de comandos, `Consulta.saldo` string con patrón de dos decimales, ejemplo `OK_CONSULTA`, `E510` en `423` con `intentos` entero y `additionalProperties: false`, texto de `POST /__reset`, resumen de `E506`). `info.version` sigue en `1.0.0`. El catálogo de `app/catalogo.py` copia esos cuerpos. `CHANGELOG.md` anota los tres cambios bajo `[Unreleased]`. `pyproject.toml` y `uv.lock` no cambian de versión. Los dos estándares de versionamiento ganan la excepción de reemplazo incompatible en las rutas vigentes.
- Código: `app/configuracion.py` (`LIMITE_TRANSFER`), `app/estado.py` (contador `intentos` por cuenta, borrado en `reset`), `app/motor.py` (formato de `saldo`, tope, `E510` con `intentos`). El saldo interno sigue siendo entero.
- Pruebas: unitarias nuevas que fallan primero (`pruebas/unitarias/`, en particular `test_motor.py`, `test_estado.py` y `test_catalogo.py`); luego se actualizan las que hoy exigen `100000`, `saldo` entero o `E510` en `409`. El replay de `pruebas/contrato/test_replay.py` deja `experimentos.jsonl` y toma las secuencias de la tarde. Las pruebas de contrato del OpenAPI siguen exigiendo que el catálogo coincida con los ejemplos.
- `docs/architecture/doc-diseno.md`: el caso C3 y la tabla de estado. El docstring de `validar_limite` en `app/motor.py` pasa a decir `50000`. `docs/architecture/plan-incidente.md` queda como plan previo.
- `herramientas/pasos.py` todavía afirma el contrato de la mañana (`409` `E510`, `saldo` entero). Hay que alinearlo con la tarde para que el humo local no falle en falso. `herramientas/` sigue fuera de las reglas del paquete desplegable.
