# Jonathan Vallejo Munoz — Doc de diseño: Reto 2 · La caja negra

> **Equipo:** Jonathan Vallejo Munoz · **Reto elegido:** 2 · **Versión:** entrega 12:00

> Las líneas `🔎 EV` son evidencia temporal para revisión; se borran antes de entregar. «log N» = línea N de `experimentos.jsonl`; «H-xx» = `hallazgo.md`; «Dxx» = `tech-decisions.md`.

---

## 1. Entendimiento del problema

**Qué tiene que resolver el sistema:**
El sistema recibe mensajes de texto de un mini banco (`COMANDO;args;control`) y debe responder con el **mismo status y el mismo cuerpo** que el servicio original, incluidos los errores y su orden, manteniendo el estado de cuentas y operaciones entre requests.

> 🔎 EV: README («responda exactamente igual, errores incluidos»); H-C1–H-C9, H-M1–H-M5

**Entrada y salida del entrypoint:**

| | Formato | Ejemplo |
|---|---|---|
| Entrada | `POST /msg` · `Authorization: Bearer <token>` · `{"m": "COMANDO;args;control"}` | `{"m":"DEPOSITO;AC-0001;250000;86"}` |
| Salida | Status HTTP + cuerpo JSON exacto | `200 {"status":"recieved","operacionId":"OP-0001"}` |

> 🔎 EV: README (contrato); log 7 (ejemplo)

**Restricciones y límites conocidos:**
- **Tiempo por caso:** 5 s por paso.
- **Costo:** $0 por caso, porque el clon no usa LLM. Explorar el original tiene un tope de 10 req/s y 8.000 req/día.
- **Entorno:**
  - El clon **no** puede llamar al original: si lo hace, el set vale 0.
  - Los tokens mueren a las 20:00.
  - El set le habla a un solo proceso.
  - Los headers no se comparan.

> 🔎 EV: README (5 s, límites de token, «el set vale 0», 20:00, un solo proceso, «los headers no se comparan»); D20

---

## 2. Supuestos, casos difíciles y alcance

### 2.1 Supuestos

| # | Supuesto | Estado | Cómo lo validamos |
|---|---|---|---|
| S1 | El servicio no cambia antes de las 20:00 | Por validar | Repetir los 20 ejemplos y casos clave por la tarde (D18) |
| S2 | Orden de entrada: **ruta + método (E404) → auth (E001) → JSON (E100)**. *Antes suponíamos la auth primero; la prueba lo refutó* | Confirmado | Ruta inexistente y `GET /msg` sin token → E404; `/msg` sin token y no-JSON → E001 |
| S3 | `HALT` responde siempre E520. *No se encontró ningún mecanismo de confirmación* | Por validar | Ya se descartaron 5 mecanismos (argumento, reenvío, campo en el cuerpo, header y query); no se seguirá explorando (D19) |
| S4 | En empate de `sugerencia` gana el comando **alfabéticamente menor**. *Antes suponíamos el orden de la lista; la prueba lo refutó* | Confirmado | 6 empates entre pares distintos |
| S5 | Strikes: E506 **y E507** suman; solo un DEPOSITO exitoso **al propio origen** o un TRANSFER exitoso como origen reinician el contador (un depósito a otra cuenta no); PING, CONSULTA, ALTA, recibir transferencia y E202 no lo tocan | Confirmado | Una seq por acción: 2 strikes → acción → 2 TRANSFER |
| S6 | Métodos PUT/DELETE/PATCH/OPTIONS/HEAD en `/msg` → E404 | Confirmado | Un request por método |
| S7 | No hay tope de cuentas ni de operaciones. *No se buscó; el tope de saldo sí se descartó (109999999989 aceptado)* | Por validar | Barrido de ALTA (costo alto: baja prioridad) |
| S8 | Railway corre una sola instancia y no reinicia durante la evaluación | Por validar | Configurar 1 réplica sin autoescalado |
| S9 | El token del equipo es el mismo token de participante con el que exploramos | Confirmado | Dato del equipo |
| S10 | `sugerencia` compara en mayúsculas | Confirmado | `pong`→PING, `altas`→ALTA |
| S12 | `/docs`, `/redoc` y `/openapi.json` responden E404 en el original, por eso el clon las desactiva. *Nunca se probaron; se infiere de H-E4 (toda ruta no registrada → E404)* | Por validar | 3 GET con token (decidido: no se prueban) |

> 🔎 EV:
> - S1: H-D1 (log 2–21, solo mañana).
> - S2: log 925–933.
> - S3: log 803, 909–923, 1173–1183.
> - S4: log 935–940 (HANG→HALT y PLTG→ALTA descartan el orden de la lista), 814.
> - S5: log 941–1012 (E507 bloquea: 1000–1003), 714–720 (TRANSFER exitoso reinicia), 1028–1036 (depósito a otra cuenta no reinicia).
> - S6: log 575, 1014–1018.
> - S7: pendiente 4 en hallazgo.md; saldo sin tope: log 1265–1278.
> - S8: README («cada una tendrá su propio estado»).
> - S9: confirmado por Jonathan (dueño del token).
> - S10: log 1038, 1039.
> - S12: inferencia de H-E4 (log 575–578, 925–928, 1196–1198); sin prueba directa.

### 2.2 Casos difíciles que anticipamos

| # | Caso | Por qué es difícil | Cómo lo manejamos |
|---|---|---|---|
| C1 | Orden de los errores | Hay 16 validaciones y gana la primera; un orden distinto cambia el error | Pipeline en el orden observado, configurable (D13) |
| C2 | Dígito de control | La fórmula no era evidente; los caracteres no ASCII y los ceros a la izquierda tienen trampas | ISO 7064 MOD 97-10 solo sobre letras y dígitos ASCII; el control se compara como texto (H-I4, H-I5) |
| C3 | Bloqueo por strikes | Es estado oculto: 3 TRANSFER rechazados (E506/E507) bloquean desde el cuarto intento con `423` e `intentos`; un DEPOSITO exitoso a la propia cuenta desbloquea y reinicia `intentos`, uno a otra cuenta no | Contador de strikes e `intentos` por cuenta; el rechazo responde `423` (H-M5) |
| C4 | `sugerencia` en E301 | Aparece solo a veces | Levenshtein ≤ 2; empate → alfabético (D22) |
| C5 | Texto exacto | Hay rarezas: `"recieved"`, espacio final en E301, `cuentaId` vs `cuenta_id` | Catálogo único de cuerpos copiados del log (D12) |
| C6 | Respuestas por defecto del framework | FastAPI responde por su cuenta 404 `{"detail":...}` y 422 de validación | Manejadores propios para toda ruta y error |
| C7 | `PING` no valida el control | Rompe la regla general: con 2 segmentos responde pong sea cual sea el control; con más → E302 | Excepción explícita en el pipeline (H-I7) |
| C8 | Cambia la fórmula del control durante el día | Hoy está deducida para la versión de la mañana; descubrirla de nuevo cuesta requests | Validador de control aislado y parametrizado (D25): las variantes de la misma familia se cambian por config; un algoritmo nuevo cambia una sola función |
| C9 | No vemos el set de evaluación antes de la entrega | El set oculto (100 tests) solo corre en la entrega final y no repite `ejemplos.jsonl`; solo cubrimos lo que exploramos | Explorar con el LLM antes de las 20:00 los casos con más riesgo; lo no explorado responde el error más probable, marcado como supuesto (D20) |

> 🔎 EV:
> - C1: hallazgo.md §5; log 590–599, 603, 874, 875, 880, 896–899.
> - C2: H-I5 (log 409–557, 900–907); no ASCII: 1208–1212; `02` vs `2`: 1206, 1207; 959 respuestas coherentes (H-I8).
> - C3: log 694–697, 893–896, 722, 1000–1003.
> - C4: D22 (explica todos los E301 de los logs, incluidos 6 empates y 2 en minúsculas: 935–940, 1038, 1039).
> - C5: log 7, 4, 6, 13.
> - C6: *supuesto técnico* (comportamiento estándar de FastAPI, no probado aquí).
> - C7: log 23–27, 890, 891; 1043–1050, 1171, 1172.
> - C8: *supuesto de riesgo* (README: «el servicio puede cambiar durante el día»); costo del primer descubrimiento: ~157 requests (log 408–564); D25.
> - C9: README («Ningún test repite la secuencia de `pruebas/ejemplos.jsonl`»); el set solo corre en la entrega final (confirmado por Jonathan).

### 2.3 Fuera de alcance (y por qué)

| Qué dejamos fuera | Razón |
|---|---|
| Header `X-Req` | Los headers no se comparan |
| Ejecutar un `HALT` real | No se encontró cómo confirmarlo; detener el clon haría fallar el resto de los tests |
| Persistir el estado si el proceso se reinicia | Cada test empieza con `/__reset` |
| Fallback LLM | El clon no puede consultar al original; un LLM solo adivinaría |
| Holdout de casos | Se usa todo el log para iterar |

> 🔎 EV:
> - X-Req: README («los headers no se comparan»).
> - HALT: D19.
> - Persistencia: D11; README («cada test empieza con POST /__reset»).
> - Fallback LLM: D20.
> - Holdout: D14.

---

## 3. Arquitectura

Diagramas: ver [`arquitectura.md`](arquitectura.md).

| Componente | Responsabilidad | Tecnología |
|---|---|---|
| Entrypoint | Recibe todas las rutas y métodos; `/health`, `/__reset`, `/msg`; el resto → E404 | FastAPI (preferencia del equipo: más experiencia → más velocidad para implementar y cambiar; ver D1) |
| Pipeline de validación | Aplica las 16 validaciones en orden; la primera que falla responde | Python, orden en config |
| Motor de comandos | Ejecuta PING, ALTA, CONSULTA, DEPOSITO, TRANSFER, ANULA y HALT | Python |
| Estado en memoria | Cuentas, saldos, operaciones, contadores AC/OP, strikes e `intentos` del bloqueo `423` | Diccionario en el proceso |
| Validador de control | Calcula y compara el dígito de control. Parámetros en config: qué caracteres cuentan y cómo, fórmula (módulo, constantes), comparación (texto/número) y comandos exentos | Python, parámetros en config |
| Catálogo de respuestas | Status + cuerpo exacto de cada error y respuesta OK | Tabla en config |
| Logs | Un registro por request: método, ruta, cuerpo, status, respuesta y paso del pipeline, **sin el header `Authorization`**. Sirve para depurar | stdout JSON (logs de Railway) |

> 🔎 EV: D1, D11, D12, D13, D25; hallazgo.md §5 (pipeline), H-I4, H-I5, H-I7 (reglas del control)

**Regla dura:** el clon conoce el token del equipo (que es el mismo de participante) solo para validar la auth, y no tiene código que llame al original. El código vive en dos carpetas: `clon/` (lo único que va a Railway) y `herramientas/` (scripts de exploración y medición, solo locales), así que el clon no puede llamar al original ni por accidente.

> 🔎 EV: README («el reemplazo no puede llamar al original… el set vale 0»); D17, D26

**Flujo de un caso:**
1. Ruta + método: solo `POST /msg`, `POST /__reset` y `GET /health`; si no → E404.
2. Auth: el `Bearer` debe ser exactamente el token del equipo; si no → E001.
3. JSON (si no → E100) y `m` string (si no → E102).
4. Separar por `;` → segmentos vacíos (E104), falta de control (E103), formato del control (E201) y su valor (E202), salvo en PING.
5. Comando (E301 + `sugerencia`), aridad (E302), monto (E303), origen igual a destino (E304).
6. Reglas de negocio contra el estado: cuenta (E401), HALT (E520) u operación (E402), bloqueo (E510), límite (E506), saldo (E507).
7. Ejecutar, actualizar el estado y responder desde el catálogo.

> 🔎 EV: hallazgo.md §5; log 925–933 (ruta antes que auth); H-E3 (case-sensitive `Bearer`, log 574); H-I7

**Manejo de fallas:** no hay llamadas externas, así que no se necesitan timeouts ni reintentos. Una excepción interna inesperada responde **500** (*supuesto*: el original nunca devolvió un 500 en 1.286 requests, así que no hay un cuerpo que copiar), con el cuerpo en **texto plano `Internal Server Error`**, que es el estándar.

> 🔎 EV: el log no tiene ningún status 500 (ids 1–1286); decisión del equipo (D23)

---

## 4. Decisiones y trade-offs

| # | Decisión | Alternativa descartada | Por qué elegimos así | Qué sacrificamos |
|---|---|---|---|---|
| D1 | Clon 100 % determinista, sin LLM | Fallback LLM para casos no explorados | Hay que coincidir carácter por carácter y el clon no puede consultar al original | Lo no explorado depende de nuestros supuestos |
| D2 | Pipeline con el orden observado y catálogo único de respuestas, ambos en config | Orden y textos fijos en el código | Reproduce el orden y los textos exactos (rarezas incluidas); si cambian el orden o los textos, se ajusta sin tocar la lógica | Algo más de indirección; un comando o una regla nueva sí requieren código |
| D3 | El LLM solo explora el original antes de las 20:00 (sub-agentes con revisión humana); lo aprendido se convierte en reglas deterministas | LLM dentro del clon (en tiempo real o aprendiendo en segundo plano) | El clon no puede consultar al original y el set solo corre en la entrega final: el LLM solo sirve donde puede ver respuestas reales | Lo no explorado antes de las 20:00 queda como supuesto |
| D4 | Estado en memoria por proceso | SQLite / archivo | Cada test empieza con reset y hay un solo proceso; es simple y rápido | Se pierde si el proceso se reinicia |
| D5 | `sugerencia` = Levenshtein ≤ 2; empate → alfabético | Explorar más; nunca sugerir | Explica todos los E301 del log, incluidos 6 empates | No hay empates probados entre comandos largos |

> 🔎 EV:
> - D1: D4 + D20; README («el set vale 0»).
> - D2: D12 + D13; log 7, 13.
> - D3: D20, D21; README («el set vale 0», tokens hasta las 20:00); set solo en la entrega final (confirmado por Jonathan).
> - D4: D11.
> - D5: D22; log 757–819, 886, 887, 935–940.

---

## 5. Plan para medir

### 5.1 Set de evaluación propio

| Tipo de caso | Cantidad | Fuente |
|---|---|---|
| Casos normales (200/201 en `/msg`) | 283 pasos | `experimentos.jsonl` |
| Casos de error, incluidos los límite (control, montos, límite 100000, strikes) | 936 pasos | `experimentos.jsonl` |
| Ejemplos oficiales | 20 pasos | `pruebas/ejemplos.jsonl` |
| Casos nuevos (holdout) | 0 | No se reservan |

Se excluye la seq `c2`, que no empieza con reset; en su lugar se usa `c2b`.

> 🔎 EV: conteo del log (1.286 líneas: 283 OK en `/msg`, 936 errores, 61 a `/__reset`, 6 a `/health`; 63 seqs); D14; log 558–564 vs 900–907

### 5.2 Métricas

| Métrica | Cómo se calcula | Objetivo |
|---|---|---|
| Coincidencia en replay | Pasos con el mismo status y cuerpo / total de pasos del log | **100 %** |
| Tasa de crashes | Pasos sin respuesta válida / total | 0 % |
| Latencia | Máximo por paso | < 5 s |
| Costo | USD por caso | $0 (sin LLM) |
| Set oficial | Tests que pasan en `/evento/resultados` | Seguimiento, sin objetivo propio |

> 🔎 EV: README (criterio de igualdad y 5 s); D14; D20

### 5.3 Cómo lo corremos

Herramientas (carpeta `herramientas/`, solo locales): `q.py` manda un request al original y lo registra en el log; `sweep.py` busca el control válido de un mensaje; `ctl.py` calcula el control; `replay.py` repite el log contra el clon y compara.

```
python herramientas/replay.py --url http://localhost:8000 --log experimentos.jsonl --ejemplos pruebas/ejemplos.jsonl
```

El replay hace reset al inicio de cada seq y compara cada paso igual que el evaluador: JSON sin importar el orden de las claves; si no es JSON, texto exacto. Se corre en cada cambio y antes de cada deploy.

**Cómo reproduce cada línea** (el formato del log lo fija el README y no tiene campos para el método, la ruta ni la auth):
- **Método, ruta y auth**: se leen del prefijo `[MÉTODO RUTA auth]` de la hipótesis. Sin prefijo = `POST /msg` con el token propio; `[POST /__reset]` = reset con el token propio.
- **Auth**: «token propio», «sin token», «token inválido»/«token ajeno», «sin prefijo Bearer», «'Bearer' sin token» y «'bearer' en minúscula».
- **Cuerpo**: objeto → JSON; texto → se manda tal cual (`""` = cuerpo vacío); `"-"` = sin cuerpo.

> 🔎 EV: README (cómo se comparan las respuestas; campos del log). Las 61 líneas con prefijo se leen bien (verificado con regex). Log 586 corregido de `{}` a `""` (era un cuerpo vacío). El nombre del script es tentativo.

---

## 6. Riesgos y cambios en el entorno

**Cómo detectamos que algo cambió:**
- Repetir contra el original los 20 ejemplos y una seq de humo que cubra los 16 errores, después de las 15:30 y antes del último deploy (D18).
- Una respuesta del original que no coincide con la del log, o que trae un código de error nuevo.
- Una caída del % en `/evento/resultados`.
- Controles conocidos de la seq de humo que pasan a dar E202 → cambió la fórmula del control.

**Plan de respuesta:** detectar → reproducir con un caso → actualizar la config o el catálogo → re-correr el replay → documentarlo en la spec (§6 Cambios durante el día).

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| El servicio cambia por la tarde | Alta | Alto | Re-chequeo periódico; orden y textos en config |
| Cambia la fórmula del control | Media | Alto (casi todos los mensajes dan E202) | Detección con la seq de humo; re-descubrimiento con `sweep.py` (control válido por mensaje) + buscador offline de fórmulas; cambio en la config del validador (D25) |
| El set incluye un `HALT` confirmado | Baja | Bajo (1 test) | Aceptado (S3) |
| Supuestos S7 incorrectos | Media | Medio | Probarlos en la próxima tanda de exploración |
| Railway reinicia o escala el proceso | Baja | Alto | 1 réplica sin autoescalado; riesgo aceptado |
| Se agota el presupuesto de requests | Baja | Medio | Llevamos ≥1.185 de 8.000 (X-Req máximo, incluye las revisiones) |

> 🔎 EV:
> - Cambio por la tarde: README («el servicio puede cambiar durante el día»); plantilla («incidente de las 15:30»).
> - HALT: D19.
> - Railway: README («cada una tendrá su propio estado»).
> - Presupuesto: conteo del log.
> - Probabilidades: *estimación nuestra, sin evidencia*.
