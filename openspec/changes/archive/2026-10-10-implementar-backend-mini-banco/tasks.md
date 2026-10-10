# Tasks

## 1. Esqueleto del proyecto

- [x] 1.1 Crear `pyproject.toml` con `requires-python`, las dependencias exactas y la configuración de ruff, mypy, pytest, coverage y bandit que fija `docs/standards/backend-standards.md`, usando el paquete `app` y la carpeta `pruebas`. Verificar que `uv lock` genera `uv.lock` y que `uv sync --frozen` termina en 0.
- [x] 1.2 Crear `CHANGELOG.md` en `1.0.0` (Keep a Changelog, misma versión que `info.version` del contrato), el paquete `app` vacío y `pruebas/conftest.py` con las fixtures `token_prueba`, `app`, `client` y `estado_limpio`. Verificar que esos archivos existen y que `uv run python -c "import pruebas.conftest"` termina en 0.

## 2. Catálogo y errores

- [x] 2.1 Implementar `app/errores.py` (`ErrorDominio`) y `app/catalogo.py` (`CodigoError`, status y cuerpos copiados de los ejemplos del contrato, sin leer el YAML en runtime). Verificar con `uv run pytest pruebas/unitarias/test_catalogo.py pruebas/unitarias/test_errores.py` que el catálogo cubre todo el enum y que cada cuerpo coincide con `components.examples`.
- [x] 2.2 Añadir las pruebas de contrato del OpenAPI (estructura 3.1 válida, `info.version` igual a la versión del proyecto, ejemplos sin huérfanos y status alineados al catálogo). Verificar con `uv run pytest pruebas/contrato/test_openapi.py`.

## 3. Dígito de control

- [x] 3.1 Implementar `app/control.py` (ISO 7064 MOD 97-10, letras y dígitos ASCII, resto ignorado, comparación textual). Verificar con `uv run pytest pruebas/unitarias/test_control.py` los casos de letra, no ASCII, cadena vacía y `02` distinto de `2`.

## 4. Estado en memoria

- [x] 4.1 Implementar `app/estado.py`: cuentas, saldos, operaciones, strikes, correlativos `AC`/`OP` y `reset()`. Verificar con `uv run pytest pruebas/unitarias/test_estado.py` el reset a `0001`, que un depósito suma y una transferencia mueve los dos saldos, que anular un depósito gastado deja saldo negativo, que anular una transferencia revierte ambos lados, que `ANULA` no consume el correlativo `OP`, que la segunda anulación no mueve saldos y el contador de strikes.

## 5. Pipeline y motor

- [x] 5.1 Implementar `app/configuracion.py` y `app/pipeline.py` con el orden de la spec, la exención de control de `PING` (sin saltar `E104`) y el monto de 1 a 10 dígitos sin ceros a la izquierda. Verificar con `uv run pytest pruebas/unitarias/test_pipeline.py` que gana el primer fallo (`E303` antes de `E304`, `E304` antes de `E401`, `E201` antes del comando), que `PING;` y `PING;X;` responden `E104`, que un segundo segmento no vacío de `PING` no aplica `E202`, y que `m` igual a `""` responde `E103`.
- [x] 5.2 Implementar `app/motor.py` (PING, ALTA, CONSULTA, DEPOSITO, TRANSFER, ANULA, HALT sin detener el proceso). Verificar con `uv run pytest pruebas/unitarias/test_motor.py` alta con saldo 0, depósito, transferencia en el límite `100000`, `E506`, `E507`, `E510` al cuarto intento, desbloqueo por depósito propio, `HALT` con un argumento respondiendo `E520` sin cambiar el estado y `HALT` sin argumentos respondiendo `E302`.

## 6. Entrada HTTP, auth y logs

- [x] 6.1 Implementar `app/entrada.py` (`crear_app`, ruta comodín, handlers, lectura del cuerpo con `request.body` y `json.loads`, fail-fast si falta `APP_AUTH_TOKEN`) y `app/registro.py` (JSON a stdout y redacción del token). Verificar con `uv run pytest pruebas/unitarias/test_entrada.py pruebas/unitarias/test_registro.py` rutas, métodos, `HEAD` con cuerpo vacío, barra final, query string, `500` en texto plano, que una lista o un string JSON responden `E102` y no `500`, y que el token no aparece en el log.
- [x] 6.2 Añadir las pruebas marcadas `security` de autorización (incluida la variante no ASCII, que responde 401 y no 500) y de ausencia de clientes de red en `app` y en las dependencias de runtime. Verificar con `uv run pytest -m security`.
- [x] 6.3 Reescribir el `README.md` de la raíz para que alguien corra el proyecto solo con ese archivo: requisito Python 3.13 y uv, `uv sync --frozen`, variable `APP_AUTH_TOKEN`, comando de tests, `uv run uvicorn app.entrada:app` con un worker y sin access log, y el despliegue con `railway.toml` (token solo como variable de Railway). El criterio es «corre siguiendo el README y el código se explica solo»: el README no reexplica el dominio. Verificar ejecutando, en ese orden, los comandos de instalación y de tests que el propio README escriba, y que `uv run python -c "from app.entrada import app"` termina en 0.
- [x] 6.4 Dejar `railway.toml` en la raíz con Railpack, `uv sync --frozen --no-dev`, el arranque del estándar, `numReplicas` 1, `overlapSeconds` 0, `sleepApplication` falso y sin `healthcheckPath` ni token. Verificar con `uv run pytest pruebas/contrato/test_railway.py`.

## 7. Integración

- [x] 7.1 Implementar el replay en proceso de `docs/architecture/experimentos.jsonl` como lo fija la spec: prefijo de `hipotesis` con el orden de auth, objeto como JSON, texto tal cual, `"-"` sin cuerpo, estado limpio al empezar cada secuencia incluida y sin descartar las que no abren con reset. Excluir solo `c2`. Verificar con `uv run pytest pruebas/contrato/test_replay.py` que cada paso coincide en status y cuerpo y termina en menos de 5 segundos.
- [x] 7.2 Correr la tabla de calidad del estándar, en orden: `ruff format --check`, `ruff check`, `mypy`, `pytest` con cobertura de ramas ≥ 90 % sobre `app`, `bandit` y `pip-audit`. Verificar que cada comando termina en 0.
