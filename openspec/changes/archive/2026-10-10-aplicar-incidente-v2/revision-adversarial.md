# Revisión adversarial

Revisión de `proposal.md`, `design.md`, `specs/mini-banco/spec.md` y `tasks.md` contra el pedido original, `docs/architecture/INCIDENT.md`, `docs/architecture/incidente-experimentos.jsonl`, `docs/standards/openapi.yml` y los estándares de documentación y backend.

El pedido original exige tres cosas en el proposal: actualizar la documentación (incluido `docs/standards/openapi.yml` si el contrato cambia), cubrir los comportamientos con pruebas unitarias, y hacerlo en este orden: primero las unitarias nuevas en rojo, después el cambio, después la misma suite en verde.

La delta sí nombra documentación, unitarias y ese orden. Los tres cambios de `INCIDENT.md` están en la spec. La lista de secuencias de ids 93–346 coincide con el log: 17 secuencias, de `humo-1601-h1` a `humo-1618-h4`. Cada `h2`–`h4` y cada `inc-*` abre con reset; las `h1` no tocan cuentas. Los hallazgos son lo que, aun así, queda mal cerrado.

## Alta

### 1. El contrato queda a medias si se sigue la lista del diseño

`design.md` acota el cambio de `docs/standards/openapi.yml` a `info.version`, `Consulta.saldo` como string, el ejemplo `OK_CONSULTA` en `"0.00"`, `E510` solo en `423`, `409` solo con `E520`, el resumen de `E506` y la línea 14 del orden de validación.

En el mismo archivo siguen vigentes, y ninguna tarea las nombra:

| Lugar | Texto que sigue describiendo la mañana |
|---|---|
| `info.description` | «(v1, sin versión en la ruta)» |
| Tabla de comandos | `` `200 {"cuenta_id":"AC-000N","saldo":N}` `` |
| `Consulta.saldo` | `type: integer` y «Puede ser negativo tras un ANULA», sin la regla entero/100 ni un patrón de dos decimales |
| `POST /__reset` | Reinicia cuentas, operaciones, saldos, strikes y correlativos. No menciona `intentos` |
| Esquema nuevo de `423` | El diseño pide `error`, `mensaje` e `intentos` obligatorios, y no fija `intentos` como entero ni `additionalProperties: false` |

El log guarda `intentos` como número (`inc 136`, `inc 225–227`) y el saldo como string con dos decimales (`inc 116`, `inc 163`, `inc 166`, `inc 169`, `inc 174`, `inc 254`). Un schema string sin patrón acepta `"40000"` igual que `"400.00"`. El proposal dice «descripción del saldo y del tope»; el diseño no escribe esa descripción.

Para cerrarlo: la tarea del contrato tiene que nombrar la descripción de `info`, la tabla de comandos, la descripción y el patrón de `saldo`, el texto de `/__reset`, y el tipo entero de `intentos` con `additionalProperties: false`.

### 2. Publicar `2.0.0` deja los estándares y el lock en la regla anterior

`docs/standards/documentation-standards.md` §5 y `docs/standards/backend-standards.md` §2 reservan MAJOR a una ruta nueva `/v2/...`. MINOR es un cambio compatible en las rutas que ya existen. El proposal declara el supuesto de `2.0.0` sin `/v2` y las tareas no modifican esas dos tablas.

`uv.lock` fija el paquete `app` en `1.0.0`. La tarea 2.2 sube `pyproject.toml` y `CHANGELOG.md`, y no regenera el lock. El deploy de los estándares usa `uv sync --frozen`.

Para cerrarlo: o la versión elegida cabe en la tabla vigente, o el mismo cambio actualiza las dos tablas y `uv.lock`. La entrada `## [2.0.0]` tiene que quedar bajo las secciones de Keep a Changelog, con `[Unreleased]` arriba.

### 3. El criterio de salida de la tarea 2.1 no puede cumplirse

La tarea 2.1 pone `info.version` en `2.0.0` y exige que pase `uv run pytest pruebas/contrato/test_openapi.py pruebas/unitarias/test_catalogo.py`. `test_openapi_version_igual_proyecto_coincide` compara `info.version` con `version` de `pyproject.toml`. Esa versión sigue en `1.0.0` hasta la tarea 2.2.

Quien siga el orden escrito ve rojo en el paso que la tarea marca como verde, y puede subir el YAML y el proyecto en desorden o debilitar el test de versión.

Para cerrarlo: contrato, catálogo, `pyproject.toml`, `uv.lock` y changelog comparten un solo criterio de salida, el test de versión incluida.

### 4. La tarea 2.3 corrige evidencia histórica y deja la regla viva sin dueño

La tarea pide que las frases vigentes de `docs/architecture/doc-diseno.md` pasen a decir `50000` y `423`. En ese archivo:

- El único `100000` está en §5.1 y describe el corpus de la mañana: «límite 100000» medido en `experimentos.jsonl`. Ese log sigue siendo la mañana; cambiar el número falsifica el conteo.
- No hay una frase «E510 en 409». El `409` visible en la evidencia de C2 es un rango de ids (`log 409–557`), el tramo donde se ajustó el dígito de control.

Lo que sí describe el clon vigente y la tarea no nombra:

- C3: el bloqueo sigue contado solo en strikes, sin status `423` ni `intentos`.
- La tabla de estado: cuentas, saldos, operaciones, correlativos y strikes. No entra el contador nuevo.
- `app/motor.py`, docstring de `validar_limite`: «por encima de 100000». La tarea 2.4 cambia la constante y no el texto público.
- `docs/architecture/plan-incidente.md` sigue instruyendo un clon con límite `100000`. El proposal no lo actualiza ni lo marca como evidencia intocable, al contrario de `hallazgo.md`, los simulacros e `INCIDENT.md`.

Para cerrarlo: reescribir la tarea sobre C3, la tabla de estado y el docstring del tope. Dejar intactos el conteo de `experimentos.jsonl` y los ids `409–557`. Decidir en el proposal si `plan-incidente.md` se actualiza o se conserva como plan previo al incidente.

## Media

### 5. Las unitarias rojas no amarran los síntomas medidos y citan ids que no son el caso

La tarea 1.1 pide `"0.00"`, `"123.45"`, `"0.05"`, `"1234567.89"`, `"-5.00"`, `"99999999.99"` y `"-0.01"`, y manda citar en `ids` los inc 163, 166, 169, 174 y 254.

Esos cinco ids son, en orden, `"123.45"`, `"0.05"`, `"1234567.89"`, `"-5.00"` y `"99999999.99"`. `"0.00"` está en el inc 116. `"-0.01"` no aparece en `incidente-experimentos.jsonl`. El estándar de documentación prohíbe citar una fuente que no exista. El escenario tampoco está en el delta de la spec; solo en el diseño y en la tarea. Quien archive la spec no exige ese caso, y quien siga la tarea lo presenta como evidencia del incidente.

La tarea 1.2 dice que `pytest -k limite_transfer` falla «porque `100000` todavía pasa». Las pruebas que la tarea manda a escribir son otras: `50000` se acepta hoy, los depósitos `100001` y `123456789` se aceptan hoy, y `50001` hoy también se acepta. El rojo real es ese último caso. El síntoma medido, `TRANSFER` `100000` y `99999` en `422 E506` (inc 118, 120 y 149), no está en el grupo rojo.

La tarea 3.1 dice «actualizar» `test_motor_transfer_en_limite_100000_acepta` y no dice el oráculo nuevo. El nombre y el cuerpo actuales afirman que `100000` se acepta. Reescribirlo como otro `50000` aceptado deja el síntoma del humo sin unitaria.

Tampoco entran al grupo rojo los efectos en cadena que `INCIDENT.md` atribuye al cambio 2 dentro de `humo-1601-h3`: `ANULA;OP-0002` pasa a `404 E402` (inc 124 y 125) porque ese `OP` ya no se emite, y las consultas quedan en `"5000.00"` y `"0.00"` (inc 127 y 128). El único candado de esos cuatro pasos es el replay completo, que corre después del código.

Para cerrarlo: cada `ids` cita el inc de ese caso; `"-0.01"` se marca como consecuencia de la fórmula, sin id de incidente, o se agrega al delta si se exige. El grupo rojo incluye `100000` y `99999` como `E506` (inc 118, 120, 149) y la cadena inc 124, 125, 127 y 128. La tarea 3.1 dice que el test de `100000` espera `E506`.

### 6. El rechequeo de dos strikes no tiene escenario ni tarea

`INCIDENT.md` reconfirma el umbral: con dos strikes no bloquea (inc 221). En el log, tras dos `E506`, `TRANSFER` de `40000` responde `200` (inc 221). Ese éxito reinicia el episodio: hacen falta otros tres `E506` (inc 222–224) para el `E510` con `intentos` 1 (inc 225).

El requirement lo dice en una frase («con dos strikes la cuenta no se bloquea») y el delta no trae escenario. La tarea 1.3 lista intentos 1, 2 y 3, el reinicio por depósito, tres `E507`, `ANULA` y el bloqueo solo como origen. No lista el inc 221. El test viejo `test_motor_cuarto_intento_responde_e510` solo mira que el cuarto rechazo sea `E510`. El inc 221, un `TRANSFER` dentro del tope nuevo mientras ya hay dos strikes, queda solo dentro del replay de `inc-e510-1`.

Para cerrarlo: un escenario y una unitaria del grupo rojo para el inc 221, con el reinicio que demuestran los inc 222–225.

## Baja

### 7. La tarea 3.2 no nombra el test que sigue exigiendo la mañana

`pruebas/contrato/test_replay.py` tiene `test_replay_incluye_secuencia_sin_reset`, que exige `adv-a5`, excluye `c2` y exige `c2b`. Esas secuencias son de `experimentos.jsonl`. La tarea 3.2 cambia el archivo al log de la tarde y dice que `pytest pruebas/contrato/test_replay.py` pasa, sin nombrar ese test. El escenario nuevo de la spec sí sustituye el caso: la secuencia sin reset pasa a ser `humo-1601-h1`.

Quien solo cambie la ruta del log y el rango de ids deja ese test en rojo por un motivo que la tarea no describe.

Para cerrarlo: la tarea 3.2 nombra `test_replay_incluye_secuencia_sin_reset` y lo alinea con el escenario `humo-1601-h1`.
