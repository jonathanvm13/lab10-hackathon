# Hallazgos — La caja negra

Los ids de evidencia son líneas de `experimentos.jsonl`. Los requests de las revisiones externas se integraron al log (ids 1040–1217).
**Confianza**: confirmado (probado y repetido) · probable (visto una vez o inferido) · supuesto (no probado).

## Resumen
Es un **mini banco** con estado por token. Recibe `{"m": "COMANDO;args;control"}` en `POST /msg`.
Comandos: `PING`, `ALTA`, `CONSULTA`, `DEPOSITO`, `TRANSFER`, `ANULA` y uno oculto, `HALT` (destructivo).

## 1. Entrada

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| H-E1 | `POST /__reset` → `200 {"ok":true}`; el estado vuelve a cero (contadores AC/OP desde 0001) | 1, 22, 29, 132, 565 | confirmado |
| H-E2 | `GET /health` con token → `200 {"ok":true}` (sin token → 401 E001, ver H-E3) | 566, 1020 | confirmado |
| H-E3 | Sin token, con token inválido, sin prefijo `Bearer`, `Bearer` sin token o `bearer` en minúscula → `401 {"error":"E001","mensaje":"no autorizado"}`. Aplica en `/health`, `/__reset` y `/msg` | 567–574 | confirmado |
| H-E4 | Ruta inexistente (GET/POST), `GET /` o método distinto de POST en `/msg` (GET, PUT, DELETE, PATCH, OPTIONS, HEAD) → `404 {"error":"E404","mensaje":"ruta desconocida"}`. `HEAD /msg` responde 404 **con cuerpo vacío**. Se evalúa **antes que la auth**: da E404 incluso sin token o con token inválido | 575–578, 925–928, 931, 1014–1018; `GET /__reset`, `POST /health` y `/msg/` con barra final → E404: 1196–1198 | confirmado |
| H-E5 | Cuerpo que no es JSON, o cuerpo vacío → `400 {"error":"E100","mensaje":"json inválido"}`. La auth va antes: sin token y con cuerpo no-JSON → E001 | 579, 586, 929, 930, 933 | confirmado |
| H-E6 | JSON sin `m`, `{}` o `m` que no es string (número, null, lista) → `400 {"error":"E102","mensaje":"falta m"}` | 580–583, 587 | confirmado |
| H-E7 | `m: ""` → E103 "falta control" | 584, 1021 | confirmado |
| H-E8 | Las claves extra junto a `m` se ignoran. Si `m` viene duplicada en el JSON, gana la **última** | 585, 1022, 1184, 1285, 1286 | confirmado |
| H-E9 | **Sin trim**: `" PING;64"` → E301 (con `sugerencia`); `"CONSULTA; AC-0001"` → E401 | 886, 889 | confirmado |
| H-E10 | `X-Req` es un contador acumulado de requests a `/msg` con auth OK (incluye los errores). **No** se reinicia con `/__reset`, y `/__reset` no trae el header | 21→23, todo el log | confirmado |

## 2. Integridad

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| H-I1 | El mensaje se separa por `;`. Si hay un segmento vacío (`PING;`, `ALTA;;85`, `ALTA;Pipe;;47`, `;` final o doble) → `400 {"error":"E104","mensaje":"segmento vacío"}` | 627, 645–647 | confirmado |
| H-I2 | Si solo viene el comando, sin control → `400 {"error":"E103","mensaje":"falta control"}` | 28, 595 | confirmado |
| H-I3 | Control que no es exactamente 1–2 dígitos ASCII (`5X`, `182`, `082`, `-1`, `1.5`, espacios…) → `400 E201 "control mal formado"` | 18, 130, 131, 591, 619–630 | confirmado |
| H-I4 | Control de 1–2 dígitos pero con valor incorrecto → `400 E202 "control inválido"`. Se compara **como texto**: `02` con control correcto 2 → E202 | 3, 30–129, 593, 1024, 1025; 1206, 1207 | confirmado |
| H-I5 | **Fórmula (ISO 7064 MOD 97-10)**: sobre el mensaje sin control, cada **letra ASCII** (a–z/A–Z) entra como 1..26 en decimal y cada **dígito ASCII** 0–9 tal cual; todo lo demás se ignora, incluidos los caracteres no ASCII (`ß`, `٣`, `²`). `N = int(cadena or "0")`; `control = 98 - (N*100) % 97` (rango **2..98**) | ajuste 409–552; predicciones 553–557, 903–905; bordes 563, 564, 901, 902, 906, 907; no ASCII: 1027 (`ı` se ignora, no se convierte en I), 1169, 1170 (`ñ` se ignora; tratarla como `n` da E202), 1208–1212; coherente con 959 respuestas de los 3 logs | confirmado |
| H-I6 | El control cubre el comando: `CONSULTa` = `CONSULTA`, `alta;nina` es válido | 12, 905 | confirmado |
| H-I7 | `PING` (sin distinguir mayúsculas) **no** valida el control: con 2 segmentos responde pong sea cual sea el control (`XX`, `100`, `082`, `5X`). Con más segmentos → E302; `PING` solo → E103; `PING;` o `PING;X;` → E104. También acepta controles no ASCII (`ñ`) o largos (50 caracteres) | 23–28, 645, 890, 891; 1043–1050, 1171, 1172, 1280–1283 | confirmado |
| H-I8 | La fórmula (H-I5) y la comparación como texto (H-I4) son coherentes con 959 respuestas de `experimentos.jsonl`, `revision-experimentos.jsonl` y `revision-adversarial.jsonl`, sin excepciones | 3 logs | confirmado |

```python
def control(msg_sin_control: str) -> int:
    d = ""
    for ch in msg_sin_control:
        if "a" <= ch <= "z" or "A" <= ch <= "Z":
            d += str(ord(ch.upper()) - 64)
        elif "0" <= ch <= "9":
            d += ch
    return 98 - (int(d or "0") * 100) % 97


# válido si el texto del control == str(control(...))
```

## 3. Comandos

El comando no distingue mayúsculas, pero no tolera espacios. Los IDs de cuenta y operación **sí** distinguen mayúsculas (`ac-0001` → E401).

| ID | Comando | Args | Efecto / respuesta | Evidencia | Confianza |
|---|---|---|---|---|---|
| H-C1 | `PING` | 0 | `200 {"pong":true}`. Con args → E302 | 2, 23–27, 890, 891 | confirmado |
| H-C2 | `ALTA;nombre` | 1 | `201 {"cuentaId":"AC-000N"}`, saldo 0. Acepta nombres repetidos, con espacios (literales), `_`, dígitos y 200 caracteres | 4, 112, 838, 888, 903–905 | confirmado |
| H-C3 | `CONSULTA;cuenta` | 1 | `200 {"cuenta_id":"AC-000N","saldo":N}` | 6, 823, 831 | confirmado |
| H-C4 | `DEPOSITO;cuenta;monto` | 2 | `200 {"status":"recieved","operacionId":"OP-000N"}`. Sin límite de negocio y **sin tope de saldo** (llegó a 109999999989). Si es a la propia cuenta, **desbloquea** (ver H-M5) | 7, 683, 722, 1061–1063, 1265–1278 | confirmado |
| H-C5 | `TRANSFER;orig;dest;monto` | 3 | Igual que DEPOSITO; mueve el saldo | 8, 11, 714 | confirmado |
| H-C6 | `ANULA;opId` | 1 | `200 {"ok":true,"anulada":"OP-000N"}`; revierte un DEPOSITO (resta) o una TRANSFER (ambas cuentas). Si se repite → `200 {"ok":false,"motivo":"ya anulada"}`. Op inexistente, mal formada o en minúsculas (`op-0002`) → E402 sin cambiar saldos. Funciona aunque la cuenta esté bloqueada, pero **no la desbloquea** | 14, 15, 848, 850, 854, 861, 862, 1153, 1162–1164, 1254, 1255 | confirmado |
| H-C7 | `HALT;arg` (**oculto**) | 1 | `409 {"error":"E520","mensaje":"operación destructiva: detiene el servicio; reenvía con confirmación"}`. Las palabras CONFIRMAR, CONFIRMO, CONFIRMACION, CONFIRM, CONFIRMED, SI, YES y OK como argumento siguen dando E520. Reenviar el mismo mensaje tampoco confirma, ni los campos `confirmacion`, `confirmar`, `confirm` o `confirmado` en el cuerpo, ni los headers `X-Confirm`, `X-Confirmacion`, `X-Confirmation` o `Confirm`, ni la query `?confirm=` / `?confirmacion=`, ni los argumentos `CONFIRMACIÓN`, `REENVIA` o `FORCE`. **No se encontró el mecanismo de confirmación.** El clon responde E520 a todo HALT con aridad válida | 803, 909–923, 1173–1183 | confirmado (E520); confirmación: supuesto |
| H-C8 | Comando desconocido → `400 {"error":"E301","mensaje":"comando desconocido "}`. Si está a distancia de Levenshtein ≤ 2 de uno real, agrega `"sugerencia":"<CMD>"` (PONG→PING, HELP→HALT, ALTAS→ALTA…). En empate gana el **alfabéticamente menor** (HANG→HALT, PLTG→ALTA, NULT→ANULA). Compara en mayúsculas y devuelve el comando en mayúsculas (`pong`→PING, `altas`→ALTA) | 13, 757–819, 886, 935–940, 1038, 1039 | confirmado |
| H-C9 | ~40 verbos de banco probados (RETIRO, PAGO, SALDO, MOVIMIENTOS, RESET…) dan todos E301 | 757–799 | confirmado |

### Montos (DEPOSITO, TRANSFER)
| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| H-A1 | Válido = entero de 1–10 dígitos, sin signo, sin decimales y sin ceros a la izquierda; `0` no vale. Si no → `400 {"error":"E303","mensaje":"monto inválido"}` | 632–638, 661, 683, 684 | confirmado |
| H-A2 | Límite de TRANSFER: **≤ 100000 OK, > 100000 → `422 E506 "límite excedido"`**, por operación (no acumulado) | 714, 715, 893; 5 × 100000 seguidas = OK: 1064–1070 | confirmado |
| H-A3 | TRANSFER con origen igual a destino → `400 {"error":"E304","mensaje":"origen y destino iguales"}` | 836, 874 | confirmado |

## 4. Memoria entre requests

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| H-M1 | IDs secuenciales por token: `AC-000N` y `OP-000N` (4 dígitos). `/__reset` los reinicia | 4, 5, 245, 821, 846 | confirmado |
| H-M2 | Solo DEPOSITO y TRANSFER exitosos consumen un OP. ANULA, consultas y errores no lo hacen | 10, 11, 851, 857 | confirmado |
| H-M3 | Las ALTA fallidas no consumen AC | 245 | confirmado |
| H-M4 | ANULA puede dejar **saldo negativo**, en el origen (−1000) o en el destino de una TRANSFER que ya gastó (−700) | 873, 1165–1168 | confirmado |
| H-M5 | **Bloqueo por strikes**: un strike es un TRANSFER saliente rechazado por **E506 o E507** (se suman mezclados). Con 3 strikes sin un reinicio en medio (no hace falta que sean requests consecutivos), el tercero devuelve su propio error y desde el siguiente TRANSFER como origen → `409 {"error":"E510","mensaje":"cuenta bloqueada"}`. **Reinician** el contador: DEPOSITO exitoso a la propia cuenta (también desbloquea) y TRANSFER exitoso como origen. **Neutrales** (ni suman ni reinician): PING, CONSULTA, ALTA, recibir una transferencia, depósito a otra cuenta, E202, E303, E304 y E401. **No desbloquean**: ANULA (aunque se ejecuta) ni un DEPOSITO fallido. El bloqueo solo afecta a la cuenta como origen | 694–697, 714–723, 743–754, 893–896, 941–1012, 1028–1036, 1076–1081, 1086–1101, 1109–1112, 1117–1144, 1218–1264 | confirmado |

## 5. Errores

Pipeline (gana el primer fallo):
1. **E404** ruta + método (404)
2. **E001** auth (401)
3. **E100** JSON (400)
4. **E102** `m` (400)
5. **E104** segmento vacío / **E103** falta control (400)
6. **E201** formato del control (400) — *no aplica a PING*
7. **E202** valor del control (400) — *no aplica a PING*
8. **E301** comando (400)
9. **E302** aridad (400)
10. **E303** monto (400)
11. **E304** origen = destino (400)
12. **E401** cuenta (404)
13. **E520** HALT (409) / **E402** operación (404)
14. **E510** bloqueo (409)
15. **E506** límite (422)
16. **E507** saldo (422)

| Código | Status | Cuerpo exacto | Evidencia orden |
|---|---|---|---|
| E001 | 401 | `{"error":"E001","mensaje":"no autorizado"}` | 567–574, 929, 930 (antes que E100) |
| E404 | 404 | `{"error":"E404","mensaje":"ruta desconocida"}` | 575–578, 925–928, 931 (antes que E001) |
| E100 | 400 | `{"error":"E100","mensaje":"json inválido"}` | 579, 586 |
| E102 | 400 | `{"error":"E102","mensaje":"falta m"}` | 580–583 |
| E103 | 400 | `{"error":"E103","mensaje":"falta control"}` | 28, 595 (antes que E301) |
| E104 | 400 | `{"error":"E104","mensaje":"segmento vacío"}` | 627, 645–647 |
| E201 | 400 | `{"error":"E201","mensaje":"control mal formado"}` | 591, 596 (antes que E301/E302) |
| E202 | 400 | `{"error":"E202","mensaje":"control inválido"}` | 593, 594, 598 |
| E301 | 400 | `{"error":"E301","mensaje":"comando desconocido "}` (+ `sugerencia` opcional) | 590 (antes que E302) |
| E302 | 400 | `{"error":"E302","mensaje":"aridad inválida"}` | 21, 599, 890 |
| E303 | 400 | `{"error":"E303","mensaje":"monto inválido"}` | 603 (antes que E401), 875 (antes que E304), 898 (antes que E510) |
| E304 | 400 | `{"error":"E304","mensaje":"origen y destino iguales"}` | 874 (antes que E401), 1111 (antes que E510) |
| E401 | 404 | `{"error":"E401","mensaje":"cuenta inexistente"}` | 16, 901, 899, 1112 (antes que E510 y E506) |
| E402 | 404 | `{"error":"E402","mensaje":"operación inexistente"}` | 861, 862 |
| E520 | 409 | `{"error":"E520","mensaje":"operación destructiva: detiene el servicio; reenvía con confirmación"}` | 803 |
| E510 | 409 | `{"error":"E510","mensaje":"cuenta bloqueada"}` | 896 (antes que E506), 1003 (antes que E507) |
| E506 | 422 | `{"error":"E506","mensaje":"límite excedido"}` | 880 (antes que E507) |
| E507 | 422 | `{"error":"E507","mensaje":"saldo insuficiente"}` (cuenta como strike) | 17, 735, 1000–1003 |

## 6. Cambios durante el día

| ID | Observación | Evidencia | Confianza |
|---|---|---|---|
| H-D1 | Al repetir los 20 ejemplos todo coincide: sin cambios respecto a la mañana | 2–21 | confirmado |

## 7. Riesgos (lo que un cliente nuevo no debería heredar)
- **HALT** detiene el servicio con solo una confirmación (H-C7).
- **ANULA permite saldo negativo** (H-M4).
- **Bloqueo automático** con estado oculto tras 3 TRANSFER rechazados (E506/E507), que se limpia solo con un DEPOSITO exitoso a la propia cuenta (H-M5).
- Rarezas en el texto: `"recieved"`, `cuentaId` vs `cuenta_id`, espacio final en E301.
- Sin trim; IDs que distinguen mayúsculas pero comandos que no; `m` no-string tratado como ausente.

## Pendiente
1. ~~Confirmación de HALT~~: se probaron 3 mecanismos (palabra como argumento, reenvío, campo en el cuerpo) y todos dan E520. Queda como supuesto.
2. ~~Repetir H-E2, H-E7 y H-E8~~ hecho (1020–1022).
3. Re-explorar por la tarde (detectar cambios).
4. Tope de cuentas/operaciones y `m` muy largo. (Métodos y tope de saldo: hechos, H-E4 y H-C4.)
5. ~~Qué reinicia el contador de strikes~~ hecho (H-M5).
6. ~~`sugerencia` en minúsculas~~ hecho (1038, 1039).
