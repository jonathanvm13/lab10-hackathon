# Simulacro 2 del plan de incidente — 15:27

> Segundo ensayo de `plan-incidente.md`, ahora con **dos cambios simulados de tipos distintos**. Los requests están en `simulacro2-experimentos.jsonl` (se citan como «s2 N»). No se modificó ningún archivo existente; `INCIDENT.md` no se tocó.

## Resultado

**El servicio original no ha cambiado a las 15:29.** El plan detectó, clasificó y descartó los dos cambios simulados en ~2,5 minutos.

| Paso del plan | Qué se hizo | Evidencia | Duración |
|---|---|---|---|
| 1. Detección real | `humo.py` contra la línea base real | s2 1–46: **0 cambios** | 26 s |
| 1b. Detección simulada | Copia temporal con la base alterada en 2 casos: E301 sin espacio final y umbral de strikes > 3 | s2 47–92: **2 cambios detectados**, exit 1 | 27 s |
| 2. Clasificación | Cambio A (s2 63): texto → catálogo. Cambio B (s2 90): umbral de strikes → config | s2 63, 90 | — |
| 3. Confirmación A | ZZZQ y PONG siguen respondiendo `"comando desconocido "` con espacio final | s2 93–94 | 26 s (todo 3–4) |
| 3. Confirmación B | Reset + setup + 3 × E506 → el 4º TRANSFER da **E510** | s2 95–102 | |
| 4. Exploración del borde B | Con solo 2 strikes, el TRANSFER pasa → el umbral es exactamente 3 | s2 103–109 | |
| Veredicto | **Falsas alarmas (las dos)**: el «antes» de la base no coincidía con `hallazgo.md` | — | — |
| 5. Revisar el resto | Reset + los 20 de `ejemplos.jsonl` | s2 110–130: **0 diferencias** | 19 s |
| 6. Documentar | Este archivo | — | — |

## Lecciones nuevas

| # | Lección | Acción sugerida |
|---|---|---|
| 1 | El humo detecta varios cambios en una sola corrida y cada uno se clasifica por separado | Abrir un «Cambio N» en `INCIDENT.md` por cada línea del reporte |
| 2 | Un cambio de umbral necesita explorar **los dos lados** del borde (3 bloquea, 2 no) para fijar el valor nuevo | En el paso 4, siempre probar N−1 y N |
| 3 | Anotar la conclusión después de ver la respuesta (marca `PENDIENTE` y luego completar) funcionó bien | Usarlo en el incidente real |
| 4 | Se volvió a improvisar la repetición de `ejemplos.jsonl` | Sigue faltando una herramienta para eso (pendiente de aprobación) |
| 5 | Costo del simulacro: 130 requests | Presupuesto suficiente |
