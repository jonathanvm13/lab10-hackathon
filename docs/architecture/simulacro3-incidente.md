# Simulacro 3 del plan de incidente — 15:30

> Tercer ensayo de `plan-incidente.md`, ahora con los dos tipos que faltaban: **fórmula del control** y **orden de validación**. Los requests están en `simulacro3-experimentos.jsonl` (se citan como «s3 N»). No se modificó ningún archivo existente; `INCIDENT.md` no se tocó.

## Resultado

**El servicio original no ha cambiado a las 15:32** (ya dentro de la ventana esperada del cambio). El plan detectó, agrupó y descartó los cambios simulados en ~2 minutos.

| Paso del plan | Qué se hizo | Evidencia | Duración |
|---|---|---|---|
| 1. Detección real (15:30) | `humo.py` contra la línea base real | s3 1–46: **0 cambios** | 27 s |
| 1b. Detección simulada | Copia temporal con la base alterada en 3 casos | s3 47–92: **3 diferencias detectadas**, exit 1 | 26 s |
| 2. Clasificación | 3 diferencias → **2 causas**: control (s3 60, 70: controles conocidos daban E202) y orden (s3 65: antes ganaba E202, ahora E302) | s3 60, 65, 70 | — |
| 3–4. Control | `sweep.py` sobre `CONSULTA;AC-1;{c}` → único válido 5. `ctl.py` predice bien 2 mensajes nuevos (34, 55) y el vecino 35 da E202 → la fórmula no cambió | s3 93–102 | 12 s (todo 3–4) |
| 3–4. Orden | Mismo mensaje con aridad mala: control válido → E302, control incorrecto → E202, mal formado → E201 → el orden no cambió | s3 103–105 | |
| Veredicto | **Falsas alarmas (las 3)** | — | — |
| 5. Revisar el resto | Reset + los 20 de `ejemplos.jsonl` | s3 106–126: **0 diferencias** | 19 s |
| 6. Documentar | Este archivo | — | — |

## Lecciones nuevas

| # | Lección | Acción sugerida |
|---|---|---|
| 1 | Varias diferencias pueden venir de **una sola causa** (las 2 del control) | Agrupar por causa antes de abrir un «Cambio N» en `INCIDENT.md` |
| 2 | Para el orden, la prueba clave es **el mismo mensaje con un solo fallo distinto cada vez** (válido / incorrecto / mal formado) | Usar ese patrón si cambia el orden |
| 3 | `sweep.py` escribe líneas **sin `conclusion`** (no cumple el formato de 8 campos) | Completar la conclusión después, o ajustar `sweep.py` (pendiente de aprobación) |
| 4 | `sweep.py` es barato si el control válido es bajo (7 requests) y caro si es alto (hasta 100) | Elegir plantillas con control bajo usando `ctl.py` |
| 5 | Se volvió a improvisar la repetición de `ejemplos.jsonl` (3ª vez) | Sigue faltando esa herramienta (pendiente de aprobación) |
| 6 | Costo del simulacro: 126 requests | Presupuesto suficiente |
