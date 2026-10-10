# Spec Delta

## Purpose

El mini banco recibe mensajes `COMANDO;args;control` y responde el mismo status y el mismo cuerpo que el contrato, manteniendo cuentas, saldos, operaciones y strikes entre requests del mismo proceso.

Los cuerpos exactos son los ejemplos de `docs/standards/openapi.yml`. Esta spec no los copia: cada escenario que nombra un ejemplo exige ese status y ese valor, carácter por carácter en el texto y como objeto JSON cuando el cuerpo es JSON.

## ADDED Requirements

### Requirement: Rutas y métodos conocidos

El servicio SHALL exponer solo `POST /msg`, `GET /health` y `POST /__reset`, sin prefijo de versión. Cualquier otra combinación de ruta y método SHALL responder el ejemplo `E404` antes de evaluar la autorización. `HEAD` en cualquier ruta SHALL responder `404` con cuerpo vacío. Una barra final SHALL ser una ruta desconocida, sin redirección. La query string SHALL ignorarse al identificar la ruta.

#### Scenario: Ruta inexistente sin token

- **WHEN** llega `GET /` sin header `Authorization`
- **THEN** la respuesta es el ejemplo `E404`

#### Scenario: Método no soportado en /msg

- **WHEN** llega `GET`, `PUT`, `DELETE`, `PATCH` u `OPTIONS` sobre `/msg`
- **THEN** la respuesta es el ejemplo `E404`

#### Scenario: HEAD sin cuerpo

- **WHEN** llega `HEAD /msg`
- **THEN** el status es `404` y el cuerpo está vacío

#### Scenario: Query string no cambia la ruta

- **WHEN** llega `POST /msg?confirm=1` con un mensaje `PING` válido y token válido
- **THEN** la respuesta es el ejemplo `OK_PING`

### Requirement: Autorización

Toda ruta conocida SHALL exigir `Authorization` igual a `Bearer <token>` con el esquema `Bearer` exacto, un espacio y el token configurado. Sin header, token distinto, sin prefijo, `Bearer` sin token o `bearer` en minúscula SHALL responder el ejemplo `E001`. La comparación SHALL ser en tiempo constante sobre bytes. Un token con caracteres no ASCII SHALL responder `E001` y SHALL NOT responder `500`.

#### Scenario: Token válido en health

- **WHEN** llega `GET /health` con el token configurado
- **THEN** la respuesta es el ejemplo `OK`

#### Scenario: Bearer en minúscula

- **WHEN** llega `POST /msg` con `Authorization: bearer <token>` y un JSON válido
- **THEN** la respuesta es el ejemplo `E001`

#### Scenario: Ruta desconocida gana a la auth

- **WHEN** llega `GET /msg` sin token
- **THEN** la respuesta es el ejemplo `E404`

### Requirement: Cuerpo JSON de /msg

`POST /msg` con token válido SHALL leer el cuerpo como JSON. Cuerpo vacío o no JSON SHALL responder el ejemplo `E100`. Si falta `m`, `m` no es string, `m` es `null`, o el JSON no es un objeto, SHALL responder el ejemplo `E102`. `m` igual a `""` SHALL responder el ejemplo `E103`, no `E104`. Las claves extra SHALL ignorarse. Si `m` viene duplicada, SHALL ganar la última.

#### Scenario: Cuerpo vacío

- **WHEN** llega `POST /msg` con token válido y cuerpo vacío
- **THEN** la respuesta es el ejemplo `E100`

#### Scenario: m numérico

- **WHEN** llega `POST /msg` con token válido y `{"m": 1}`
- **THEN** la respuesta es el ejemplo `E102`

#### Scenario: JSON que no es objeto

- **WHEN** llega `POST /msg` con token válido y el cuerpo es `["PING;64"]` o `"PING;64"`
- **THEN** la respuesta es el ejemplo `E102` y no es `500`

#### Scenario: m cadena vacía

- **WHEN** llega `POST /msg` con token válido y `{"m": ""}`
- **THEN** la respuesta es el ejemplo `E103`

### Requirement: Orden de validación del mensaje

Para `POST /msg` autenticado, el servicio SHALL aplicar este orden y SHALL responder el primer fallo, con el ejemplo del contrato: `E100`, `E102`, `E104`, `E103`, `E201`, `E202`, `E301`, `E302`, `E303`, `E304`, `E401`, `E520` o `E402`, `E510`, `E506`, `E507`. `PING` SHALL omitir `E201` y `E202`, y SHALL NOT omitir `E104`: un segmento vacío sigue siendo `E104`. El comando SHALL compararse sin distinguir mayúsculas. Los identificadores `AC-NNNN` y `OP-NNNN` SHALL distinguir mayúsculas. Los segmentos SHALL separarse por `;` sin recortar espacios.

#### Scenario: Segmento vacío antes que el control

- **WHEN** el mensaje es `ALTA;;<control>` con control de uno o dos dígitos
- **THEN** la respuesta es el ejemplo `E104`

#### Scenario: Solo el comando

- **WHEN** el mensaje es `ALTA` sin `;`
- **THEN** la respuesta es el ejemplo `E103`

#### Scenario: Control de tres dígitos antes que el comando

- **WHEN** el mensaje es `ZZZQ;100`
- **THEN** la respuesta es el ejemplo `E201`

#### Scenario: PING con segmento vacío

- **WHEN** el mensaje es `PING;` o `PING;X;`
- **THEN** la respuesta es el ejemplo `E104`

#### Scenario: PING no valida el control

- **WHEN** el mensaje tiene exactamente dos segmentos, el comando es `PING` y el segundo segmento no está vacío
- **THEN** la respuesta es el ejemplo `OK_PING`

#### Scenario: PING con aridad de más

- **WHEN** el mensaje `PING` tiene más de dos segmentos y ninguno está vacío
- **THEN** la respuesta es el ejemplo `E302`

### Requirement: Dígito de control

Salvo `PING`, el control SHALL ser uno o dos dígitos ASCII. Su valor SHALL calcularse con ISO 7064 MOD 97-10 sobre el mensaje sin el control: cada letra ASCII vale 1..26, cada dígito ASCII vale tal cual, el resto de caracteres se ignora, `N` es el entero de esa cadena o `0` si queda vacía, y `control = 98 - (N * 100) % 97`. La comparación SHALL ser textual: `02` no es `2`. Un formato inválido SHALL responder `E201`. Un valor distinto SHALL responder `E202`.

#### Scenario: Control correcto de ALTA

- **WHEN** el primer mensaje tras un reset es `ALTA;Lucia;82`
- **THEN** la respuesta es el ejemplo `OK_ALTA`

#### Scenario: Ceros a la izquierda

- **WHEN** el control calculado es `2` y el mensaje envía `02`
- **THEN** la respuesta es el ejemplo `E202`

### Requirement: Comando desconocido y sugerencia

Un comando que no es `PING`, `ALTA`, `CONSULTA`, `DEPOSITO`, `TRANSFER`, `ANULA` ni `HALT` SHALL responder el ejemplo `E301` cuando ningún comando real está a distancia de Levenshtein ≤ 2, comparando en mayúsculas. Si hay uno o más a distancia ≤ 2, SHALL responder el ejemplo `E301_SUGERENCIA` con `sugerencia` igual al comando real de menor distancia y, en empate, el alfabéticamente menor.

#### Scenario: Sin sugerencia

- **WHEN** el comando no se parece a ninguno real dentro de distancia 2 y el control es válido
- **THEN** la respuesta es el ejemplo `E301`

#### Scenario: Sugerencia PING

- **WHEN** el comando es `PONG` y el control es válido
- **THEN** la respuesta es el ejemplo `E301_SUGERENCIA`

#### Scenario: Empate alfabético

- **WHEN** dos comandos reales empatan en la distancia mínima ≤ 2
- **THEN** `sugerencia` es el alfabéticamente menor

### Requirement: Comandos que modifican estado

Tras un `POST /__reset` exitoso, la primera `ALTA` válida SHALL crear `AC-0001` con saldo 0 y responder `OK_ALTA`. Cada alta siguiente SHALL incrementar el correlativo. `CONSULTA` de esa cuenta SHALL responder `OK_CONSULTA`. `DEPOSITO` válido SHALL sumar el monto al saldo de esa cuenta y responder `OK_DEPOSITO` con el siguiente `OP-NNNN`. `TRANSFER` válido SHALL restar el monto al origen, sumarlo al destino y responder `OK_TRANSFER` con el siguiente `OP-NNNN`. Ambos usan el texto literal `recieved`. El estado SHALL conservarse entre requests del mismo proceso.

#### Scenario: Alta y consulta

- **WHEN** tras un reset se ejecuta `ALTA;Lucia;82` y luego la consulta válida de `AC-0001`
- **THEN** la alta es `OK_ALTA` y la consulta es `OK_CONSULTA`

#### Scenario: Depósito

- **WHEN** existe `AC-0001` y llega un `DEPOSITO` válido de un monto permitido
- **THEN** la respuesta sigue la forma del ejemplo `OK_DEPOSITO` y el saldo consultado aumenta en ese monto

#### Scenario: Transferencia mueve los dos saldos

- **WHEN** un `TRANSFER` válido mueve un monto del origen al destino
- **THEN** el saldo del origen baja en ese monto y el del destino sube en ese monto

### Requirement: Monto, cuentas y transferencia

Un monto SHALL ser un entero decimal positivo, sin signo y sin ceros a la izquierda, de 1 a 10 dígitos (`1`..`9999999999`). Si no, y el comando lleva monto, SHALL responder `E303` antes de mirar si la cuenta existe. `TRANSFER` con origen y destino iguales SHALL responder `E304` antes de `E401`. Una cuenta u operación citada que no existe SHALL responder `E401` o `E402`. `TRANSFER` con monto mayor que `100000` SHALL responder `E506`. `TRANSFER` con monto de `100000` o menos y saldo insuficiente en el origen SHALL responder `E507`. `DEPOSITO` SHALL NOT rechazarse por saldo.

#### Scenario: Monto cero

- **WHEN** llega `DEPOSITO` a una cuenta existente con monto `0` y control válido
- **THEN** la respuesta es el ejemplo `E303`

#### Scenario: Once dígitos

- **WHEN** llega `DEPOSITO` con monto de 11 dígitos y control válido
- **THEN** la respuesta es el ejemplo `E303`

#### Scenario: Cuenta destino inexistente antes que el saldo

- **WHEN** el origen existe con saldo 0, el destino no existe y el monto es `500`
- **THEN** la respuesta es el ejemplo `E401`

#### Scenario: Límite inclusivo

- **WHEN** el origen tiene saldo suficiente y el monto de `TRANSFER` es `100000`
- **THEN** la transferencia se acepta

#### Scenario: Por encima del límite

- **WHEN** el monto de `TRANSFER` es `120000` y ambas cuentas existen
- **THEN** la respuesta es el ejemplo `E506`

### Requirement: Anulación

`ANULA` de un depósito no anulado SHALL restar ese monto de la cuenta del depósito, aunque el saldo quede negativo. `ANULA` de una transferencia no anulada SHALL sumar el monto al origen y restarlo del destino. En ambos casos SHALL marcar la operación anulada y responder `OK_ANULA` con ese `operacionId`. `ANULA` SHALL NOT emitir un `OP` nuevo: el siguiente depósito o transferencia usa el correlativo siguiente al último emitido. Una segunda `ANULA` de la misma operación SHALL responder `OK_ANULA_YA_ANULADA` sin volver a mover saldos. `ANULA` de un id inexistente SHALL responder `E402`.

#### Scenario: Anulación repetida

- **WHEN** se anula una operación ya anulada
- **THEN** la respuesta es el ejemplo `OK_ANULA_YA_ANULADA` y los saldos no cambian

#### Scenario: Anular un depósito ya gastado

- **WHEN** se anula un depósito cuyo monto ya salió de la cuenta
- **THEN** la respuesta es `OK_ANULA` y el saldo de esa cuenta queda negativo en ese monto

#### Scenario: Anular no consume correlativo

- **WHEN** existe `OP-0001`, se anula, y el siguiente comando válido es un depósito
- **THEN** el depósito nuevo responde con `OP-0002`

### Requirement: Strikes y bloqueo

Cada `TRANSFER` del origen que responde `E506` o `E507` SHALL sumar un strike a esa cuenta origen. Al tercer strike, el siguiente `TRANSFER` de esa cuenta SHALL responder `E510` sin ejecutar la transferencia. Un `DEPOSITO` exitoso en la propia cuenta, o un `TRANSFER` exitoso como origen, SHALL reiniciar el contador de esa cuenta, también si ya estaba bloqueada. Un depósito a otra cuenta, recibir una transferencia, `PING`, `CONSULTA`, `ALTA` y `E202` SHALL NOT cambiar el contador. `E510` SHALL evaluarse antes que `E506` y `E507`.

#### Scenario: Tres rechazos bloquean el cuarto

- **WHEN** una cuenta origen acumula tres `TRANSFER` rechazados por `E506` o `E507` e intenta otro `TRANSFER`
- **THEN** la respuesta es el ejemplo `E510`

#### Scenario: Depósito propio desbloquea

- **WHEN** la cuenta origen está bloqueada y recibe un `DEPOSITO` exitoso sobre sí misma
- **THEN** un `TRANSFER` posterior válido de esa cuenta ya no responde `E510`

#### Scenario: Depósito a otra cuenta no reinicia

- **WHEN** la cuenta origen tiene strikes y deposita con éxito en otra cuenta
- **THEN** el contador de la origen no vuelve a cero

### Requirement: HALT

`HALT` con un argumento, como fija el contrato, y el control válido SHALL responder siempre el ejemplo `E520` y SHALL NOT detener el proceso ni alterar cuentas, saldos, operaciones ni strikes. Con otra cantidad de argumentos SHALL responder el ejemplo `E302`.

#### Scenario: HALT no apaga el servicio

- **WHEN** llega un `HALT` válido y después `GET /health` con token
- **THEN** el `HALT` es el ejemplo `E520` y health sigue respondiendo el ejemplo `OK`

### Requirement: Reset del estado

`POST /__reset` con token válido SHALL borrar cuentas, saldos, operaciones y strikes, y SHALL reiniciar los correlativos `AC` y `OP` en `0001`. SHALL responder el ejemplo `OK`. `GET /__reset` SHALL responder `E404`.

#### Scenario: El correlativo vuelve a empezar

- **WHEN** ya existe `AC-0001`, se llama `POST /__reset` y luego una `ALTA` válida
- **THEN** la nueva alta responde `OK_ALTA` (`AC-0001`)

### Requirement: Fallo interno y aislamiento

Una excepción no prevista SHALL responder `500` con cuerpo de texto plano igual al ejemplo `E500`. El servicio SHALL ser determinista y SHALL NOT realizar llamadas de red salientes. El token SHALL NOT aparecer en logs ni en cuerpos de error. Si el token de arranque falta o está vacío, el proceso SHALL NOT quedar sirviendo tráfico.

#### Scenario: Excepción inesperada

- **WHEN** un manejador de request deja escapar una excepción no tipada del dominio
- **THEN** el status es `500`, el contenido es texto plano y el cuerpo es el ejemplo `E500`

### Requirement: Replay de casos grabados

El servicio SHALL reproducir cada paso de `docs/architecture/experimentos.jsonl` con el mismo status y el mismo cuerpo, comparando JSON como objeto y el resto como texto exacto. Cada paso SHALL terminar en menos de 5 segundos. La secuencia `c2` SHALL excluirse porque continúa el estado de `c1`; `c2b` permanece. Las demás secuencias SHALL ejecutarse, incluidas las que no abren con reset: `adv-a1` a `adv-a6`, `humo-1319-h1`, `humo-1320-h1`, `humo-1324-h1`, `humo-1325-h1` y `humo-1326-h1`. El harness SHALL empezar cada secuencia incluida desde estado limpio y SHALL NOT inventar un reset que la línea no trae ni descartar una secuencia por no abrirlo.

Sin prefijo en `hipotesis`, el paso es `POST /msg` con el token de prueba. Con prefijo `[MÉTODO RUTA resto]`, método y ruta salen de ahí; la ruta puede traer query string. El resto fija la auth por la primera fila que coincida:

| Orden | Resto del prefijo | Header |
|---|---|---|
| 1 | contiene `'Bearer' sin token` | `Bearer` sin token |
| 2 | contiene `sin prefijo Bearer` | el token de prueba, sin la palabra `Bearer` |
| 3 | contiene `bearer` en minúscula | `bearer` más el token de prueba |
| 4 | contiene `sin token` | sin `Authorization` |
| 5 | contiene `token inválido` o `token ajeno` | `Bearer` y un token distinto del de prueba |
| 6 | contiene `token propio` | `Bearer` más el token de prueba |

Si el resto además dice `+ header <Nombre>: <valor>`, el paso SHALL enviar ese header y seguir usando el token propio. Un objeto en `request` SHALL enviarse como JSON. El texto `"-"` SHALL enviarse sin cuerpo. Cualquier otro texto SHALL enviarse tal cual, y `""` es cuerpo vacío.

#### Scenario: Cobertura del log

- **WHEN** se reejecutan en proceso los pasos del log, salvo la secuencia `c2`, cada uno desde el estado limpio de su secuencia
- **THEN** cada paso coincide en status y cuerpo con la línea grabada y termina en menos de 5 segundos

#### Scenario: Cuerpo ausente no es cuerpo vacío

- **WHEN** una línea trae `request` igual a `"-"`
- **THEN** el paso se envía sin cuerpo

#### Scenario: Secuencia sin reset

- **WHEN** la secuencia es `adv-a5`
- **THEN** sus pasos se ejecutan, incluido el JSON que no es un objeto, y no se descartan por no abrir con reset

### Requirement: Despliegue en Railway

El repositorio SHALL incluir `railway.toml` en la raíz. El build SHALL usar Railpack y `uv sync --frozen --no-dev`. El arranque SHALL ser `uv run uvicorn app.entrada:app --host 0.0.0.0 --port $PORT --workers 1 --no-access-log`. SHALL haber una sola réplica (`numReplicas` = 1), sin solape con el deploy anterior (`overlapSeconds` = 0) y sin dormir la app por inactividad. El archivo SHALL NOT contener el token ni asignar `APP_AUTH_TOKEN`; esa variable se configura en Railway. SHALL NOT definir `healthcheckPath` en `/health`, porque esa ruta exige `Authorization` y el chequeo de Railway no lo envía.

#### Scenario: Una sola instancia

- **WHEN** se lee `railway.toml`
- **THEN** `numReplicas` es 1, `overlapSeconds` es 0, `sleepApplication` es falso y el comando de arranque usa `--workers 1` y el puerto `$PORT`

#### Scenario: Sin secreto en el archivo

- **WHEN** se lee `railway.toml`
- **THEN** no aparece un token ni una asignación de `APP_AUTH_TOKEN`

#### Scenario: Sin healthcheck anónimo a /health

- **WHEN** se lee `railway.toml`
- **THEN** no hay `healthcheckPath` apuntando a `/health`
