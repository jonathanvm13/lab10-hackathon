# Estándares de documentación

## 1. Docs as code

| Regla | Detalle |
|---|---|
| Ubicación | Los docs viven en el repo: `README.md` (raíz), `docs/standards/` (estándares y contrato), `docs/architecture/` (diseño y arquitectura) y el changelog del proyecto (formato Keep a Changelog) en la raíz |
| Versionado | Se versionan con el código, en el **mismo commit/PR** que el cambio que describen |
| Revisión | Un PR que cambia comportamiento sin tocar `docs/standards/openapi.yml` o el changelog del proyecto se rechaza |
| Formato | Markdown; tablas y listas antes que párrafos; diagramas en Mermaid |
| Idioma | Español |

## 2. `docs/standards/openapi.yml`: fuente de verdad del contrato

| Regla | Detalle |
|---|---|
| Fuente de verdad | `docs/standards/openapi.yml` (OpenAPI 3.1) define rutas, status y **cuerpos exactos** (sección `components.examples`) |
| Origen de los textos | Cada texto del contrato proviene de una fuente verificable (ticket, spec o caso de prueba); el código copia los textos del contrato, nunca al revés |
| FastAPI | **No** genera ni publica el contrato: `docs_url=None`, `redoc_url=None`, `openapi_url=None` (ver `docs/standards/backend-standards.md` §4.2) |
| Versión | `info.version` (SemVer) = `version` de la configuración del proyecto de uv = última entrada del changelog del proyecto |
| Nombres de ejemplos | `components.examples.<CLAVE>` con `<CLAVE>` = clave del catálogo (por ejemplo `OK`, `E000`, `E500`) |
| `summary` del ejemplo | Empieza por el status (`"400 — ..."`) y describe el caso |

### 2.1 Sincronización (prueba de contrato del OpenAPI)

Una prueba de contrato valida `docs/standards/openapi.yml` y mantiene sincronizados el contrato y el catálogo de respuestas. Debe incluir al menos:

| Test | Verifica |
|---|---|
| `test_openapi_estructura_valida_pasa` | `openapi_spec_validator.validate(yaml.safe_load(...))` sin errores |
| `test_openapi_version_igual_proyecto_coincide` | `info.version` == `version` de la configuración del proyecto de uv |
| `test_catalogo_cuerpos_igual_examples_coinciden` | Para cada clave del catálogo: `cuerpo == examples[<CLAVE>].value` (texto exacto, incluidos espacios) |
| `test_catalogo_status_igual_openapi_coincide` | El status del catálogo es la respuesta (`responses.<status>`) donde el ejemplo está referenciado |
| `test_openapi_sin_ejemplos_huerfanos_pasa` | Todo ejemplo del contrato existe en el catálogo y viceversa |

Flujo de cambio de contrato: fuente (ticket o spec) → `docs/standards/openapi.yml` → catálogo de respuestas → tests → changelog del proyecto, en el mismo cambio.

## 3. Docstrings (Google style)

| Regla | Detalle |
|---|---|
| Obligatorios | Módulos, clases y funciones/métodos **públicos** del paquete desplegable |
| Opcionales | Funciones privadas (`_x`) y tests (el nombre del test ya documenta) |
| Secciones | `Args:`, `Returns:`, `Raises:` (las palabras clave van en inglés: son parte del formato Google y las exige pydocstyle); `Example:` opcional |
| Resumen | Primera línea en imperativo o descriptiva, ≤ 100 caracteres, termina en punto |
| Idioma | **Español**, igual que el dominio y el equipo; traducir crea dos vocabularios para la misma regla |
| Cumplimiento | ruff con regla `D` y `[tool.ruff.lint.pydocstyle] convention = "google"` (ver `docs/standards/backend-standards.md` §6) |
| Tipos | No se repiten en el docstring: ya están en la firma (mypy strict) |

**Bueno:**

```python
def truncar_texto(texto: str, limite: int) -> str:
    """Trunca un texto a un número máximo de caracteres para el log.

    Cuenta caracteres Unicode, no bytes. Si el texto cabe, se devuelve sin cambios.

    Args:
        texto: Texto a truncar, p. ej. el cuerpo de la request.
        limite: Máximo de caracteres a conservar.

    Returns:
        El texto completo o sus primeros ``limite`` caracteres.

    Raises:
        ValueError: Si ``limite`` no es positivo.
    """
```

**Malo:**

```python
def trunc(t, n):
    """Trunca.

    :param t: str el texto
    :param n: int el límite
    :return: str
    """
```

Por qué es malo: sin tipos en la firma, estilo reST en vez de Google, repite tipos, no dice si cuenta caracteres o bytes ni qué pasa con límites inválidos, y los nombres `trunc`/`t`/`n` no dicen nada.

## 4. Comentarios en el código

| Sí | No |
|---|---|
| Reglas no obvias, **con su fuente**: `# Sin trim: los espacios son parte del valor (spec §3).` | Repetir lo que el código ya dice (`# suma 1`) |
| Textos literales del contrato que parecen erratas: `# Texto literal del contrato; no corregir.` | Código comentado (ruff `ERA`) |
| Por qué de un orden o una excepción (p. ej. por qué una validación va antes que otra) | Historia del cambio (eso va en git y en el changelog del proyecto) |
| `# nosec BXXX  # motivo` y `# type: ignore[código]  # motivo` | `TODO` sin dueño ni ticket |
| Supuestos: `# Supuesto: <qué> (no verificado; <por qué>).` | Datos sensibles o tokens, aunque sean de ejemplo |

## 5. Changelog del proyecto

| Regla | Detalle |
|---|---|
| Ubicación | Raíz del repo; se crea con la primera versión publicada |
| Formato | [Keep a Changelog, v1.1.0](https://keepachangelog.com/es-ES/1.1.0/) + [SemVer 2.0.0](https://semver.org/lang/es/) |
| Secciones | `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`; `[Unreleased]` arriba |
| Entrada | Una línea por cambio, con su fuente: `- Cambia el texto de E000 (ticket ABC-123).` |
| Fecha | `## [1.1.0] - AAAA-MM-DD` |

Cuándo sube la versión:

| Cambio | Versión | Ejemplo |
|---|---|---|
| Nueva versión del API expuesta en `/v2/...` (en paralelo a v1) | **MAJOR** | Un contrato incompatible publicado en una ruta nueva |
| Cambio de comportamiento compatible en las rutas existentes | **MINOR** | Un campo nuevo en una respuesta |
| Corrección para cumplir el contrato ya documentado; corrección de docs sin cambio de contrato | **PATCH** | Un texto de error que no coincidía con el contrato |
| Refactor, tests, herramientas | Sin versión (solo `[Unreleased]` si aporta) | — |

## 6. Cómo citar evidencia

Las reglas no obvias citan su fuente: ticket, spec o caso de prueba. Lo que no tiene fuente se marca como *supuesto*.

| Contexto | Formato | Ejemplo |
|---|---|---|
| Ticket | Clave del ticket | `ABC-123` |
| Spec o documento de diseño | Ruta + sección | `docs/architecture/doc-diseno.md §<n>` |
| Caso de prueba | Nombre del test o id del caso | `test_auth_bearer_minuscula_responde_401` |
| Supuesto | Palabra *supuesto* + por qué no se verificó | `supuesto: no hay casos que cubran UTF-8 inválido` |

| Dónde | Regla |
|---|---|
| Docs (`docs/**/*.md`) | Toda afirmación sobre comportamiento cita su fuente o se marca *supuesto* |
| `docs/standards/openapi.yml` | `summary`/`description` describen el comportamiento; la fuente se cita en el PR o en el changelog |
| Código | Comentario con la fuente solo en reglas no obvias (§4) |
| Tests | `ids=[...]` en `parametrize` o comentario con la fuente |
| Nunca | Citar una fuente que no exista |
