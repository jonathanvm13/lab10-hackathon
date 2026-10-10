# INCIDENT — Cambio del servicio durante el día

> Una entrada por cambio detectado. Las citas «inc N» son ids de `incidente-experimentos.jsonl`; las citas «log N» son ids de `experimentos.jsonl`.

## Resumen

El proveedor desplegó la **versión 2** sin avisar («3 comportamientos cambiaron; el resto igual que v1»). Se detectaron y midieron exactamente 3 cambios. Todo lo demás (errores de formato, control, orden de validación, E301/sugerencia, ALTA, auth, rutas) responde igual que v1 (inc 93–138 y 139–159, salvo las líneas citadas abajo).

## Línea base

- Última corrida del humo sin cambios: `humo-1536` (inc 47–92), a las 15:36.
- Línea base v2 grabada a las 16:17 (inc 255–300) y verificada con 0 cambios (inc 301–346). La base v1 se conserva en `herramientas/humo-base-v1.json`.
- Primera corrida con cambios: `humo-1601` (inc 93–138), a las 16:01: 8 diferencias. Ejemplos (inc 139–159): 8 diferencias. Todas se explican por los 3 cambios; el resto son efectos en cadena del cambio 2 (ANULA → E402, numeración de OP, saldos).

## Cambio 1 — Formato del saldo

| Campo | Valor |
|---|---|
| Hora de detección | 16:01 |
| Síntoma (antes → ahora) | `"saldo": 40000` → `"saldo": "400.00"` (inc 147) |
| Detección (corrida del humo, ids) | `humo-1601`: inc 116, 127, 128 |
| Tipo de cambio | Texto/formato de respuesta |
| Exploración (seqs e ids) | `inc-saldo-1`: inc 160–174 |
| Regla nueva confirmada | `saldo` es un **string** = valor entero / 100 con **2 decimales**, sin separador de miles, con `-` si es negativo. 12345 → `"123.45"` (inc 163); 5 → `"0.05"` (inc 166); 123456789 → `"1234567.89"` (inc 169); −500 → `"-5.00"` (inc 174). Los montos de entrada no cambian (enteros). Solo CONSULTA muestra montos |
| Impacto en el clon | Código: formateo del saldo en CONSULTA |
| Líneas «versión mañana» | 67 líneas con `saldo` en `experimentos.jsonl` (log 6 … 1828) |

## Cambio 2 — Límite de TRANSFER

| Campo | Valor |
|---|---|
| Hora de detección | 16:01 |
| Síntoma (antes → ahora) | TRANSFER 100000 → 200 ahora da **422 E506** (inc 118, 149); 99999 también (inc 120) |
| Detección (corrida del humo, ids) | `humo-1601`: inc 118, 120 |
| Tipo de cambio | Límite/umbral |
| Exploración (seqs e ids) | `inc-limite-1`: inc 175–214 (búsqueda binaria inc 180–211) |
| Regla nueva confirmada | Límite por operación de TRANSFER = **50000** (antes 100000): 50000 → 200 (inc 212); 50001 → E506 (inc 213). DEPOSITO **no** tiene límite: 100001 (inc 179) y 123456789 (inc 168) pasan. E506 sigue sumando strike al origen |
| Impacto en el clon | Config: límite de TRANSFER |
| Líneas «versión mañana» | 32 TRANSFER exitosos de más de 50000 en `experimentos.jsonl` (log 11, 714, 716 … 1820) y sus efectos en cadena |

## Cambio 3 — Respuesta de cuenta bloqueada (E510)

| Campo | Valor |
|---|---|
| Hora de detección | 16:01 |
| Síntoma (antes → ahora) | `409 {"error":"E510","mensaje":"cuenta bloqueada"}` → `423 {"error":"E510","mensaje":"cuenta bloqueada","intentos":1}` (inc 136) |
| Detección (corrida del humo, ids) | `humo-1601`: inc 136 |
| Tipo de cambio | Texto/status + regla de estado (contador nuevo) |
| Exploración (seqs e ids) | `inc-e510-1`: inc 215–236 |
| Regla nueva confirmada | Status **423**; campo nuevo `intentos` al final del cuerpo. `intentos` cuenta los TRANSFER rechazados por bloqueo: 1, 2, 3 (inc 225–227). Al desbloquear (depósito propio, inc 230–231) y volver a bloquear, **reinicia a 1** (inc 235). Sin cambios: umbral de 3 strikes (con 2 no bloquea, inc 221), desbloqueo con depósito propio, bloqueo solo como origen (CONSULTA inc 228 y TRANSFER inverso inc 229 pasan) |
| Impacto en el clon | Catálogo (status 423) + código (contador `intentos` por bloqueo) |
| Líneas «versión mañana» | 50 líneas E510 en `experimentos.jsonl` (log 697 … 1836) |

## Reglas de v1 re-confirmadas en v2 (`inc-sup-1`, inc 237–254)

- E507 como origen sigue sumando strike: 3 × E507 → el 4º TRANSFER da 423 E510 (inc 243–246).
- ANULA funciona sobre una cuenta bloqueada y no la desbloquea: `intentos` sube a 2 (inc 247–248).
- El monto sigue aceptando hasta 10 dígitos: 9999999999 pasa (inc 252) y 10000000000 da E303 (inc 253). 9999999999 → `"99999999.99"` (inc 254).
