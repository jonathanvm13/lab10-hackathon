# Casos sin cita en `citas.jsonl`

Escenarios de `openspec/specs/mini-banco/spec.md` que no tienen una línea de `docs/architecture/citas.jsonl` cuyo request y cuya respuesta coincidan con el WHEN y el THEN. Una línea cercana no cuenta.

Una línea sirve solo si el request es el del WHEN y el status y el cuerpo son los del THEN. El cuerpo esperado es el ejemplo nombrado en `docs/standards/openapi.yml`.

Logs ya revisados al armar `citas.jsonl`: `docs/architecture/incidente-experimentos.jsonl` (tarde, ids 93–346) y `docs/architecture/experimentos.jsonl` (mañana). Quedan por explorar, entre otros: `simulacro-experimentos.jsonl`, `simulacro2-experimentos.jsonl`, `simulacro3-experimentos.jsonl`, `replay-tarde-original.jsonl`, `ejemplos.jsonl`, `pruebas-prod.jsonl`, `pruebas-prod-clon.jsonl`, `pruebas-prod-original.jsonl`, `prodlog-original.jsonl` y `prodlog-clon.jsonl`. Los de producción traen status y código, sin cuerpo: no alcanzan para citar un ejemplo.

No citar como cuerpo vigente las líneas 153 y 172 de `citas.jsonl` (`vigente: false`).

## Huecos de comportamiento

### F-01 Ruta inexistente sin token

- **Spec:** escenario «Ruta inexistente sin token»
- **Buscar:** `GET /` sin header `Authorization`
- **Esperado:** ejemplo `E404` (`404`, `{"error":"E404","mensaje":"ruta desconocida"}`)
- **No vale:** `citas.jsonl` línea 1 es `GET /nope` sin token. Línea 137 es `GET /` con token.

### F-02 Query string no cambia la ruta

- **Spec:** escenario «Query string no cambia la ruta»
- **Buscar:** `POST /msg?confirm=1` con token válido y un `PING` de dos segmentos no vacíos
- **Esperado:** ejemplo `OK_PING`
- **No vale:** `citas.jsonl` línea 173 es la misma ruta con `HALT;X;42` y responde `E520`.

### F-03 m numérico

- **Spec:** escenario «m numérico»
- **Buscar:** `POST /msg` con token válido y cuerpo `{"m": 1}`
- **Esperado:** ejemplo `E102`
- **No vale:** `citas.jsonl` línea 138 es `{"m": 123}`.

### F-04 Solo el comando

- **Spec:** escenario «Solo el comando»
- **Buscar:** `m` igual a `ALTA`, sin `;`
- **Esperado:** ejemplo `E103`
- **No vale:** `citas.jsonl` línea 132 es `PING` y la 144 es `ZZZQ`. Ambas responden `E103`, pero el mensaje no es `ALTA`.

### F-05 Control correcto de ALTA

- **Spec:** escenario «Control correcto de ALTA»
- **Buscar:** el primer mensaje tras un `POST /__reset` exitoso es `ALTA;Lucia;82`
- **Esperado:** ejemplo `OK_ALTA` (`201`, `{"cuentaId":"AC-0001"}`)
- **No vale:** `citas.jsonl` línea 50 es ese mensaje y responde `OK_ALTA`, pero en la secuencia `inc-ejemplos` van antes un `PING` (línea 48) y `ALTA;Lucia;83` (línea 49).

### F-06 Ceros a la izquierda

- **Spec:** escenario «Ceros a la izquierda»
- **Buscar:** control calculado `2` enviado como `02`
- **Esperado:** ejemplo `E202`
- **No vale:** `citas.jsonl` línea 15 compara `05` con `5` (`CONSULTA;AC-1;05`).

### F-07 Depósito de 250

- **Spec:** escenario «Depósito»
- **Buscar:** `AC-0001` con saldo entero 0, luego `DEPOSITO` válido de monto `250`, luego `CONSULTA` de esa cuenta
- **Esperado:** el depósito con la forma de `OK_DEPOSITO` y la consulta con `saldo` igual a `"2.50"`
- **No vale:** `citas.jsonl` línea 53 es `DEPOSITO` de `250000`. No hay `"2.50"` en los logs revisados.

### F-08 Cuenta destino inexistente antes que el saldo

- **Spec:** escenario «Cuenta destino inexistente antes que el saldo»
- **Buscar:** origen existente con saldo entero 0, destino inexistente, `TRANSFER` de monto `500`
- **Esperado:** ejemplo `E401`
- **No vale:** `citas.jsonl` línea 31 es monto `50` y el origen ya tiene saldo del depósito de `500000`.

### F-09 Anulación repetida, saldos

- **Spec:** escenario «Anulación repetida»
- **Buscar:** segunda `ANULA` de una operación ya anulada, y una `CONSULTA` posterior de las cuentas afectadas
- **Esperado:** ejemplo `OK_ANULA_YA_ANULADA` y el mismo saldo que antes de esa segunda anulación
- **Parcial:** `citas.jsonl` línea 154 responde `{"ok": false, "motivo": "ya anulada"}`. No hay consulta después. La línea 153 es la consulta tras la primera anulación y tiene saldo entero, con `vigente: false`.

### F-10 Depósito a otra cuenta no reinicia

- **Spec:** escenario «Depósito a otra cuenta no reinicia»
- **Buscar:** la cuenta origen tiene strikes por `E506` o `E507`, deposita con éxito en otra cuenta, y el siguiente rechazo de la origen sigue el contador anterior
- **Esperado:** el contador de la origen no vuelve a cero. La prueba vigente es que el cuarto `TRANSFER` de la origen responda `423` `E510` con `intentos`, no que un `TRANSFER` de `100001` siga en `E506` (ese monto es `E506` aunque el contador se reinicie).
- **No vale:** `citas.jsonl` líneas 168–171. La línea 172 es el cuarto `TRANSFER` en `409` `E510` sin `intentos` (`vigente: false`).

### F-11 HALT no apaga el servicio

- **Spec:** escenario «HALT no apaga el servicio»
- **Buscar:** un `HALT` con un argumento y control válido, y el request siguiente es `GET /health` con token
- **Esperado:** el `HALT` es el ejemplo `E520` y health es el ejemplo `OK`
- **No vale:** `citas.jsonl` línea 20 es `HALT;X;42` → `E520`. No hay `GET /health` inmediato.

### F-12 El reset borra intentos

- **Spec:** escenario «El reset borra intentos»
- **Buscar:** una cuenta bloqueada con `intentos` mayor que 0, luego `POST /__reset`, luego una cuenta nueva que llega a `E510`
- **Esperado:** ese `E510` trae `intentos` 1 y status `423`
- **No vale:** hay resets y hay `E510` con `intentos` 1, en secuencias distintas. Ninguna encadena bloqueo, reset y un `E510` nuevo.

### F-13 Centavo negativo

- **Spec:** escenario «Centavo negativo»
- **Buscar:** una cuenta con saldo entero `-1` y su `CONSULTA`
- **Esperado:** `saldo` igual a `"-0.01"`
- **No vale:** `citas.jsonl` línea 82 muestra `"-5.00"` (entero `-500`). No hay `"-0.01"` en `incidente-experimentos.jsonl`.

### F-14 Excepción inesperada

- **Spec:** escenario «Excepción inesperada»
- **Buscar:** un request cuyo manejador responde el fallo interno
- **Esperado:** status `500`, contenido texto plano, cuerpo del ejemplo `E500` (`Internal Server Error`)
- **No vale:** no hay un `500` con ese cuerpo en los logs revisados.

## No buscar en los logs

Estos escenarios no describen una respuesta grabada. No hace falta una línea de `citas.jsonl`.

| Escenario | Qué observa |
|---|---|
| Cobertura del log | El replay compara status y cuerpo con la línea grabada y termina en menos de 5 segundos |
| La mañana no es oráculo | El replay no incluye `humo-1534-h1`, `humo-1536-h1` ni `experimentos.jsonl` |
| Cuerpo ausente no es cuerpo vacío | El paso del replay se envía sin cuerpo |
| Secuencia sin reset | Los pasos se ejecutan aunque la secuencia no abra con reset |
| Arranque | `railpack.json` arranca con `--workers 1` y el puerto `$PORT` |
| Sin secreto en el archivo | `railpack.json` no contiene el token ni `APP_AUTH_TOKEN` |
| Sin healthcheck anónimo a /health | `railpack.json` no tiene `healthcheckPath` hacia `/health` |
