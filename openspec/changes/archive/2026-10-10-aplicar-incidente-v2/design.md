# Design

## Context

El paquete `app` ya implementa la versión de la mañana. El saldo vive como `int` en `Cuenta`. `LIMITE_TRANSFER` está en `app/configuracion.py` (`100_000`). `E510` sale del catálogo con status `409` y sin campos extra. `ErrorDominio` ya acepta `campos` y `responder` los fusiona sobre el cuerpo del catálogo. Ver `proposal.md` para el motivo y `specs/mini-banco/spec.md` para el comportamiento.

## Goals / Non-Goals

**Goals:**

- Cambiar solo el formato de `CONSULTA`, el tope de `TRANSFER` y la respuesta de bloqueo, dejando el pipeline y el saldo entero como están.
- Dejar el contrato y el catálogo alineados, con la versión en `1.0.0` y los tres cambios anotados en `[Unreleased]`.
- Cubrir las reglas nuevas con pruebas unitarias escritas antes del código, y con el replay de la tarde.

**Non-Goals:**

- Una ruta `/v2` o un modo que siga respondiendo la mañana.
- Reescribir `hallazgo.md`, los simulacros, `INCIDENT.md` o `docs/architecture/plan-incidente.md`.
- Tocar el conteo de la mañana en `docs/architecture/doc-diseno.md` §5.1 o los ids `409–557`.
- Cambiar la fórmula del control, el orden de validación, la auth o los textos de los demás errores.

## Decisions

### El saldo interno sigue siendo entero

`CONSULTA` formatea al armar la respuesta. El resto de comandos no muestra montos.

`formatear_saldo(entero)` usa división entera, no `float`: signo `-` solo si `entero < 0`, luego `divmod(abs(entero), 100)` y exactamente dos dígitos. `0` es `"0.00"` (inc 116). `9999999999` es `"99999999.99"`. Un negativo no múltiplo de 100, como `-1`, es `"-0.01"`. Esa salida sigue la fórmula y no tiene línea en `incidente-experimentos.jsonl`; el delta la exige como consecuencia, sin citar un inc.

Alternativa descartada: guardar el saldo como string. Obligaría a rehacer depósitos, transferencias y anulaciones que ya operan con enteros.

### El tope sigue siendo configuración

`LIMITE_TRANSFER` pasa a `50_000`. `validar_limite` ya compara `monto > LIMITE_TRANSFER` y suma strike. `DEPOSITO` no entra en esa función. No se agrega otro tope.

### `intentos` es un contador de la cuenta, distinto de los strikes

`Cuenta` gana `intentos: int = 0`. Los strikes siguen siendo el umbral de bloqueo (3). `intentos` cuenta rechazos `E510` del episodio.

- Al bloquear, `validar_bloqueo` incrementa `intentos` y lanza `ErrorDominio(E510, campos={"intentos": n})`. No suma strike.
- `depositar` y `transferir` ya ponen strikes en 0; también ponen `intentos` en 0.
- `ANULA` no toca ninguno de los dos.
- `reset` borra las cuentas, así que borra los dos contadores.

El catálogo deja la clave `intentos` al final del cuerpo de ejemplo (`1`). `cuerpo.update` reemplaza el valor y conserva el orden. El ejemplo del contrato es ese primer rechazo. Los valores 2 y 3 los cubren las pruebas, no un segundo ejemplo.

Alternativa descartada: reutilizar strikes como `intentos`. El umbral se queda en 3 y `intentos` sigue creciendo en cada rechazo por bloqueo.

### El contrato mueve `E510` de 409 a 423

En `docs/standards/openapi.yml`:

- `info.version` se queda en `1.0.0`. No se tocan `pyproject.toml` ni `uv.lock`. La frase «v1, sin versión en la ruta» se conserva.
- `docs/standards/backend-standards.md` §2 y `docs/standards/documentation-standards.md` §5 ganan una fila de excepción, sin borrar MAJOR, MINOR ni PATCH: si el proveedor reemplaza de forma incompatible el contrato en las mismas rutas y el clon debe reflejarlo, se conserva la versión local, se actualiza el contrato y el cambio se anota bajo `[Unreleased]` con la evidencia del incidente.
- La tabla de comandos muestra `saldo` como string de dos decimales.
- `Consulta.saldo` pasa a `string`, con descripción entero/100 y patrón `^-?(0|[1-9][0-9]*)\.[0-9]{2}$`. El ejemplo `OK_CONSULTA` usa `"0.00"`.
- `409` queda solo con `E520`.
- `423` referencia un esquema propio, con `additionalProperties: false`, y `error`, `mensaje` e `intentos` obligatorios. `intentos` es entero, mínimo 1. No se abre el esquema `Error` compartido.
- El ejemplo `E510` es status `423` y trae `"intentos": 1`.
- La descripción de `POST /__reset` incluye `intentos` entre lo que se borra.
- El resumen de `E506` dice tope `50000`.
- La descripción del orden de validación dice bloqueo `423`.

`app/catalogo.py` copia status y cuerpos. Las pruebas de contrato que comparan catálogo y ejemplos tienen que seguir en verde, así que contrato y catálogo se actualizan en el mismo paso. `CHANGELOG.md` anota los tres cambios bajo `[Unreleased]`, con fuente `docs/architecture/INCIDENT.md`. La versión no sube porque entra en la excepción nueva: el original no publicó `/v2` y MAJOR sigue reservado a esa ruta.

### El replay de la tarde reemplaza al de la mañana

`pruebas/contrato/test_replay.py` lee `docs/architecture/incidente-experimentos.jsonl` y se queda con las secuencias de los ids 93–346. Cada una arranca sola: las `h2`–`h4` y las `inc-*` abren con reset; las `h1` solo prueban ruta y auth. `test_replay_incluye_secuencia_sin_reset` exige `humo-1601-h1` y deja de exigir `adv-a5`, `c2` y `c2b`. El harness actual (estado limpio por secuencia, prefijo de hipótesis, `"-"` sin cuerpo, tope de 5 segundos) se conserva. `experimentos.jsonl` no se ejecuta.

### Orden de las pruebas

Las unitarias nuevas afirman el comportamiento de la tarde contra el motor, el estado y el catálogo, y se corren antes de tocar producción: tienen que fallar. Después se cambian contrato, catálogo y código. Al final se ajustan las unitarias que todavía exigen la mañana y se corre toda la suite, replay incluido.

## Risks / Trade-offs

- [El log de la mañana deja de vigilar regresiones finas] → El humo de la tarde (`humo-1617`, `humo-1618`) y las unitarias de formato, auth y orden siguen cubriendo lo que no cambió.
- [Una secuencia de la tarde depende del estado de la anterior] → Se revisó que cada secuencia incluida abre con reset o no usa cuentas. Si el replay falla, se corrige la exclusión, no se relaja la comparación.
- [El ejemplo estático de `E510` solo muestra `intentos` 1] → Las unitarias cubren 2, 3 y el reinicio a 1. El contrato no puede enumerar el contador.
- [`herramientas/pasos.py` sigue esperando la mañana] → Se alinean sus afirmaciones de `saldo` y de `E510` para que el humo local no falle en falso. Sigue fuera del paquete desplegable.

## Migration Plan

1. Escribir y correr las unitarias nuevas; confirmar que fallan por el comportamiento de la mañana.
2. Actualizar `openapi.yml`, catálogo, configuración, estado y motor.
3. Ajustar pruebas viejas, replay, la entrada de `[Unreleased]`, la excepción de versionamiento en los dos estándares, el caso C3, la tabla de estado y el docstring de `validar_limite`.
4. Correr la suite con cobertura y el resto de la tabla de calidad de los estándares de backend.
5. Desplegar el mismo arranque (`app.entrada:app`, un worker). El estado es memoria del proceso: no hay migración de datos. Volver atrás es revertir el cambio de comportamiento; el número de versión sigue en `1.0.0`.
