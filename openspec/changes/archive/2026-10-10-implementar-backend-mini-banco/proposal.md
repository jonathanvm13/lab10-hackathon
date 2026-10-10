# Proposal

## Why

El contrato del mini banco y el diseño del clon ya están fijados, pero el repositorio no tiene paquete desplegable: no hay servicio que responda `POST /msg`, `GET /health` ni `POST /__reset`. Sin ese servicio no se puede desplegar el clon ni comprobar que status y cuerpo coinciden con el original.

## What Changes

- Crear el paquete desplegable `app` (Python 3.13, uv) que implementa el mini banco de forma determinista, con estado en memoria y sin llamadas de red salientes.
- Cubrir el contrato ya publicado: mismas rutas, el mismo orden de validación y los mismos cuerpos de `docs/standards/openapi.yml`.
- Incluir pruebas unitarias de cada módulo y pruebas de contrato (OpenAPI, catálogo y el replay del log), con cobertura de ramas ≥ 90 %. El replay excluye solo `c2`, no descarta las secuencias sin reset y exige menos de 5 segundos por paso.
- Añadir la configuración del proyecto (uv), el changelog de la primera versión `1.0.0` y el arranque con `APP_AUTH_TOKEN`.
- Reescribir el `README.md` de la raíz para que el proyecto se corra siguiendo solo ese archivo (instalar, token, tests y servidor). El código se explica solo; el README no repite el dominio.
- Añadir `railway.toml` en la raíz para desplegar una sola instancia en Railway, sin el token dentro del archivo.
- Dejar `herramientas/` fuera del paquete desplegable. No se modifica el contrato OpenAPI: ya es la fuente de verdad.

Supuesto de empaquetado: el diseño nombra la carpeta `clon/`; este cambio usa el paquete `app`, como pidió el equipo. Los estándares exigen módulos separados (y un archivo de pruebas por módulo), así que `app` es un paquete, no un único archivo.

## Capabilities

### New Capabilities

- `mini-banco`: servicio HTTP del mini banco. Recibe `COMANDO;args;control`, valida en el orden del contrato y mantiene cuentas, saldos, operaciones y strikes en memoria.

### Modified Capabilities

- Ninguna. `openspec list --specs` no devolvió capacidades existentes.

## Impact

- Código nuevo: paquete `app/`, carpeta de pruebas y `pyproject.toml` / lockfile de uv. Hoy no existe ninguno.
- API: se implementa el contrato vigente (`info.version` `1.0.0`). No hay rutas nuevas ni cambio de cuerpos.
- Dependencias de runtime: las fijadas en los estándares de backend (FastAPI y uvicorn). El paquete no incluye clientes HTTP.
- Operación: una instancia, token por `APP_AUTH_TOKEN`, logs JSON a stdout sin el token. `HALT` responde el error del contrato y no detiene el proceso.
- Fuera de este cambio: scripts de `herramientas/` y el replay contra el servicio original.
