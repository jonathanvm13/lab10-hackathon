# Spec Delta

## MODIFIED Requirements

### Requirement: Comandos que modifican estado

Tras un `POST /__reset` exitoso, la primera `ALTA` válida SHALL crear `AC-0001` con saldo entero 0 y responder `OK_ALTA`. Cada alta siguiente SHALL incrementar el correlativo. `CONSULTA` de esa cuenta SHALL responder `OK_CONSULTA`. El campo `saldo` SHALL ser un string: el entero de la cuenta dividido por 100, con exactamente dos decimales, sin separador de miles y con `-` solo si el entero es negativo. `0` SHALL mostrarse `"0.00"`. Los montos de entrada SHALL seguir siendo enteros. `DEPOSITO`, `TRANSFER` y `ANULA` SHALL NOT incluir `saldo`. `DEPOSITO` válido SHALL sumar el monto entero al saldo de esa cuenta y responder `OK_DEPOSITO` con el siguiente `OP-NNNN`. `TRANSFER` válido SHALL restar el monto al origen, sumarlo al destino y responder `OK_TRANSFER` con el siguiente `OP-NNNN`. Ambos usan el texto literal `recieved`. El estado SHALL conservarse entre requests del mismo proceso.

#### Scenario: Alta y consulta

- **WHEN** tras un reset se ejecuta `ALTA;Lucia;82` y luego la consulta válida de `AC-0001`
- **THEN** la alta es `OK_ALTA` y la consulta es `OK_CONSULTA` con `saldo` igual a `"0.00"` (`docs/architecture/INCIDENT.md`, inc 116)

#### Scenario: Depósito

- **WHEN** existe `AC-0001` con saldo entero 0 y llega un `DEPOSITO` válido de `250`
- **THEN** la respuesta sigue la forma del ejemplo `OK_DEPOSITO` y la consulta de esa cuenta muestra `"2.50"`

#### Scenario: Transferencia mueve los dos saldos

- **WHEN** un `TRANSFER` válido mueve un monto entero del origen al destino
- **THEN** la consulta del origen baja en ese monto y la del destino sube en ese monto, ambas como string con dos decimales

#### Scenario: Entero con decimales y parte menor que uno

- **WHEN** una cuenta queda con saldo entero `12345` y otra con `5`
- **THEN** sus consultas muestran `"123.45"` y `"0.05"` (`docs/architecture/INCIDENT.md`, inc 163 y 166)

#### Scenario: Sin separador de miles

- **WHEN** una cuenta queda con saldo entero `123456789`
- **THEN** la consulta muestra `"1234567.89"` (inc 169)

#### Scenario: Saldo negativo

- **WHEN** una cuenta queda con saldo entero `-500`
- **THEN** la consulta muestra `"-5.00"` (inc 174)

#### Scenario: Diez dígitos en consulta

- **WHEN** una cuenta queda con saldo entero `9999999999`
- **THEN** la consulta muestra `"99999999.99"` (inc 254)

#### Scenario: Centavo negativo

- **WHEN** una cuenta queda con saldo entero `-1`
- **THEN** la consulta muestra `"-0.01"`, consecuencia de la regla entero/100 del cambio 1 de `docs/architecture/INCIDENT.md`; no hay línea de ese valor en `incidente-experimentos.jsonl`

### Requirement: Monto, cuentas y transferencia

Un monto SHALL ser un entero decimal positivo, sin signo y sin ceros a la izquierda, de 1 a 10 dígitos (`1`..`9999999999`). Si no, y el comando lleva monto, SHALL responder `E303` antes de mirar si la cuenta existe. `TRANSFER` con origen y destino iguales SHALL responder `E304` antes de `E401`. Una cuenta u operación citada que no existe SHALL responder `E401` o `E402`. `TRANSFER` con monto mayor que `50000` SHALL responder `E506`. `TRANSFER` con monto de `50000` o menos y saldo insuficiente en el origen SHALL responder `E507`. `DEPOSITO` SHALL NOT rechazarse por saldo ni por el tope de `TRANSFER`. `E506` SHALL seguir sumando un strike al origen.

#### Scenario: Monto cero

- **WHEN** llega `DEPOSITO` a una cuenta existente con monto `0` y control válido
- **THEN** la respuesta es el ejemplo `E303`

#### Scenario: Once dígitos

- **WHEN** llega `DEPOSITO` con monto de 11 dígitos y control válido
- **THEN** la respuesta es el ejemplo `E303`

#### Scenario: Diez dígitos se aceptan

- **WHEN** llega `DEPOSITO` con monto `9999999999` y control válido a una cuenta existente
- **THEN** la operación se acepta (inc 252)

#### Scenario: Cuenta destino inexistente antes que el saldo

- **WHEN** el origen existe con saldo 0, el destino no existe y el monto es `500`
- **THEN** la respuesta es el ejemplo `E401`

#### Scenario: Límite inclusivo

- **WHEN** el origen tiene saldo suficiente y el monto de `TRANSFER` es `50000`
- **THEN** la transferencia se acepta (inc 212)

#### Scenario: Por encima del límite

- **WHEN** el monto de `TRANSFER` es `50001` y ambas cuentas existen
- **THEN** la respuesta es el ejemplo `E506` (inc 213)

#### Scenario: Tope de la mañana rechazado

- **WHEN** ambas cuentas existen, el origen tiene saldo suficiente y el monto de `TRANSFER` es `100000` o `99999`
- **THEN** la respuesta es el ejemplo `E506` (inc 118, 120 y 149)

#### Scenario: El rechazo no emite operación

- **WHEN** tras un `DEPOSITO` de `500000` que crea `OP-0001`, un `TRANSFER` de `100000` y otro de `99999` responden `E506`, y se anula dos veces `OP-0002`
- **THEN** las dos anulaciones son el ejemplo `E402`, la consulta del origen muestra `"5000.00"` y la del destino `"0.00"` (inc 124, 125, 127 y 128)

#### Scenario: Depósito por encima del tope de transferencia

- **WHEN** llega `DEPOSITO` de `100001` o de `123456789` a una cuenta existente
- **THEN** la operación se acepta (inc 179 y 168)

### Requirement: Anulación

`ANULA` de un depósito no anulado SHALL restar ese monto de la cuenta del depósito, aunque el saldo entero quede negativo. `ANULA` de una transferencia no anulada SHALL sumar el monto al origen y restarlo del destino. En ambos casos SHALL marcar la operación anulada y responder `OK_ANULA` con ese `operacionId`. `ANULA` SHALL NOT emitir un `OP` nuevo: el siguiente depósito o transferencia usa el correlativo siguiente al último emitido. Una segunda `ANULA` de la misma operación SHALL responder `OK_ANULA_YA_ANULADA` sin volver a mover saldos. `ANULA` de un id inexistente SHALL responder `E402`. La consulta posterior SHALL mostrar el saldo entero resultante con el formato de `CONSULTA`.

#### Scenario: Anulación repetida

- **WHEN** se anula una operación ya anulada
- **THEN** la respuesta es el ejemplo `OK_ANULA_YA_ANULADA` y los saldos no cambian

#### Scenario: Anular un depósito ya gastado

- **WHEN** se anula un depósito de `500` cuyo monto ya salió de la cuenta
- **THEN** la respuesta es `OK_ANULA` y la consulta de esa cuenta muestra `"-5.00"`

#### Scenario: Anular no consume correlativo

- **WHEN** existe `OP-0001`, se anula, y el siguiente comando válido es un depósito
- **THEN** el depósito nuevo responde con `OP-0002`

### Requirement: Strikes y bloqueo

Cada `TRANSFER` del origen que responde `E506` o `E507` SHALL sumar un strike a esa cuenta origen. Al tercer strike, el siguiente `TRANSFER` de esa cuenta SHALL responder `E510` sin ejecutar la transferencia y sin sumar otro strike. Esa respuesta SHALL tener status `423` y el cuerpo `{"error":"E510","mensaje":"cuenta bloqueada","intentos":N}`, con `intentos` al final. `N` SHALL ser la cantidad de `TRANSFER` rechazados por bloqueo desde el último desbloqueo, o desde el alta si no hubo desbloqueo. El primero SHALL ser el ejemplo `E510` (`intentos` 1); los siguientes SHALL ser 2 y 3. Un `DEPOSITO` exitoso en la propia cuenta, o un `TRANSFER` exitoso como origen, SHALL reiniciar strikes e `intentos`, también si ya estaba bloqueada. El siguiente episodio de bloqueo SHALL volver a empezar en `intentos` 1. Un depósito a otra cuenta, recibir una transferencia, `PING`, `CONSULTA`, `ALTA` y `E202` SHALL NOT cambiar strikes ni `intentos`. `ANULA` SHALL ejecutarse sobre una cuenta bloqueada y SHALL NOT desbloquearla ni reiniciar `intentos`. `E510` SHALL evaluarse antes que `E506` y `E507`. Con dos strikes la cuenta SHALL NOT bloquearse. El bloqueo SHALL aplicar solo cuando la cuenta es origen.

#### Scenario: Tres rechazos bloquean el cuarto

- **WHEN** una cuenta origen acumula tres `TRANSFER` rechazados por `E506` o `E507` e intenta otro `TRANSFER`
- **THEN** la respuesta es el ejemplo `E510`, con status `423` e `intentos` 1

#### Scenario: Dos strikes no bloquean y el éxito reinicia

- **WHEN** el origen acumula dos `E506` y, con saldo suficiente, hace un `TRANSFER` de `40000`
- **THEN** ese `TRANSFER` se acepta, los strikes vuelven a cero y hacen falta otros tres `E506` para que el siguiente `TRANSFER` responda `E510` con `intentos` 1 (inc 221–225)

#### Scenario: Intentos siguientes

- **WHEN** la misma cuenta bloqueada recibe otros dos `TRANSFER` como origen
- **THEN** responden `423` `E510` con `intentos` 2 y 3 (inc 225–227)

#### Scenario: Depósito propio desbloquea

- **WHEN** la cuenta origen está bloqueada y recibe un `DEPOSITO` exitoso sobre sí misma
- **THEN** un `TRANSFER` posterior válido de esa cuenta ya no responde `E510`

#### Scenario: Nuevo bloqueo reinicia intentos

- **WHEN** tras ese desbloqueo la cuenta vuelve a acumular tres strikes y hace otro `TRANSFER`
- **THEN** la respuesta es `423` `E510` con `intentos` 1 (inc 235)

#### Scenario: Depósito a otra cuenta no reinicia

- **WHEN** la cuenta origen tiene strikes y deposita con éxito en otra cuenta
- **THEN** el contador de la origen no vuelve a cero

#### Scenario: Tres E507 bloquean el cuarto

- **WHEN** una cuenta origen acumula tres `TRANSFER` rechazados por `E507` e intenta otro `TRANSFER`
- **THEN** la respuesta es `423` `E510` (inc 243–246)

#### Scenario: ANULA no desbloquea

- **WHEN** la cuenta está bloqueada con `intentos` 1, se anula una operación suya y luego intenta otro `TRANSFER`
- **THEN** `ANULA` responde éxito y el `TRANSFER` responde `423` `E510` con `intentos` 2 (inc 247–248)

#### Scenario: Bloqueo solo como origen

- **WHEN** la cuenta origen está bloqueada
- **THEN** una `CONSULTA` de esa cuenta y un `TRANSFER` hacia ella desde otra cuenta no bloqueada se aceptan (inc 228 y 229)

### Requirement: HALT

`HALT` con un argumento, como fija el contrato, y el control válido SHALL responder siempre el ejemplo `E520` y SHALL NOT detener el proceso ni alterar cuentas, saldos, operaciones, strikes ni `intentos`. Con otra cantidad de argumentos SHALL responder el ejemplo `E302`.

#### Scenario: HALT no apaga el servicio

- **WHEN** llega un `HALT` válido y después `GET /health` con token
- **THEN** el `HALT` es el ejemplo `E520` y health sigue respondiendo el ejemplo `OK`

### Requirement: Reset del estado

`POST /__reset` con token válido SHALL borrar cuentas, saldos, operaciones, strikes e `intentos`, y SHALL reiniciar los correlativos `AC` y `OP` en `0001`. SHALL responder el ejemplo `OK`. `GET /__reset` SHALL responder `E404`.

#### Scenario: El correlativo vuelve a empezar

- **WHEN** ya existe `AC-0001`, se llama `POST /__reset` y luego una `ALTA` válida
- **THEN** la nueva alta responde `OK_ALTA` (`AC-0001`)

#### Scenario: El reset borra intentos

- **WHEN** una cuenta está bloqueada con `intentos` mayor que 0, se llama `POST /__reset` y una cuenta nueva llega a `E510`
- **THEN** ese `E510` trae `intentos` 1

### Requirement: Replay de casos grabados

El servicio SHALL reproducir cada paso de las secuencias de la versión de la tarde en `docs/architecture/incidente-experimentos.jsonl`: `humo-1601-h1` a `humo-1601-h4`, `inc-ejemplos`, `inc-saldo-1`, `inc-limite-1`, `inc-e510-1`, `inc-sup-1`, `humo-1617-h1` a `humo-1617-h4` y `humo-1618-h1` a `humo-1618-h4` (ids 93–346). SHALL NOT exigir `humo-1534-h1` a `humo-1534-h4` ni `humo-1536-h1` a `humo-1536-h4` (ids 1–92), ni `docs/architecture/experimentos.jsonl`: son la versión de la mañana. Cada paso SHALL terminar en menos de 5 segundos. La comparación SHALL ser de objetos JSON cuando el cuerpo es JSON, y texto exacto en caso contrario. El harness SHALL empezar cada secuencia incluida desde estado limpio y SHALL NOT inventar un `POST /__reset` que la línea no trae ni descartar una secuencia por no abrirlo.

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

- **WHEN** se reejecutan en proceso los pasos de las secuencias de la tarde, cada uno desde el estado limpio de su secuencia
- **THEN** cada paso coincide en status y cuerpo con la línea grabada y termina en menos de 5 segundos

#### Scenario: La mañana no es oráculo

- **WHEN** se arma el conjunto de secuencias del replay
- **THEN** no incluye `humo-1534-h1`, `humo-1536-h1` ni ninguna secuencia de `docs/architecture/experimentos.jsonl`

#### Scenario: Cuerpo ausente no es cuerpo vacío

- **WHEN** una línea trae `request` igual a `"-"`
- **THEN** el paso se envía sin cuerpo

#### Scenario: Secuencia sin reset

- **WHEN** la secuencia es `humo-1601-h1`
- **THEN** sus pasos se ejecutan y no se descartan por no abrir con reset
