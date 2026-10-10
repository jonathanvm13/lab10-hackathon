# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y este proyecto adhiere a [Versionado semántico](https://semver.org/lang/es/).

## [Unreleased]

### Changed

- `CONSULTA` devuelve `saldo` como string: entero interno / 100, con dos decimales (`docs/pruebas/INCIDENT.md`).
- El tope por operación de `TRANSFER` pasa a `50000` inclusive (`docs/pruebas/INCIDENT.md`).
- `E510` responde `423` con `intentos` (`docs/pruebas/INCIDENT.md`).
- El README describe el entorno Python 3.13, la instalación de uv y las dependencias en `pyproject.toml` y `uv.lock`.

### Fixed

- Railpack encuentra el arranque en `railpack.json` (`https://railpack.com/config/file`).

### Removed

- `railway.toml`. Railpack no lo lee (`https://railpack.com/config/file`).

## [1.0.0] - 2026-10-10

### Added

- Servicio HTTP del mini banco con `POST /msg`, `GET /health` y `POST /__reset`
  (`docs/standards/openapi.yml`, spec `openspec/changes/implementar-backend-mini-banco/specs/mini-banco/spec.md`).
