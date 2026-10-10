# Simulacro del plan de incidente — 15:15

> Ensayo de `plan-incidente.md`. Los requests están en `simulacro-experimentos.jsonl` (se citan como «sim N»). No se modificó ningún archivo existente; `INCIDENT.md` no se tocó.

## Resultado

**El servicio original no ha cambiado a las 15:15.** El plan funciona de punta a punta; se ejecuta en ~1,5 minutos.

| Paso del plan | Qué se hizo | Evidencia | Duración |
|---|---|---|---|
| 1. Detección real | `humo.py` contra la línea base real | sim 1–46: **0 cambios** | 25 s |
| 1b. Detección de un cambio simulado | Copia de las herramientas en `/tmp` con la línea base alterada (TRANSFER 100000 marcado como E506) | sim 47–92: **1 cambio detectado**, exit 1 | 32 s |
| 2. Clasificación | 100000: E506 → 200 = «límite o umbral» (se ajusta por config) | sim 72 | — |
| 3. Confirmación | Reset + setup + TRANSFER 100000 → **200**, igual que en `hallazgo.md` (log 714) | sim 93–97 | 8 s |
| 4. Exploración | Borde: TRANSFER 100001 → **E506**: el límite sigue en 100000 | sim 98 | (incluido) |
| Veredicto | **Falsa alarma**: el «antes» de la base no coincidía con `hallazgo.md` | — | — |
| 5. Revisar el resto | Reset + los 20 de `ejemplos.jsonl` contra el original | sim 99–119: **0 diferencias** | 18 s |
| 6. Documentar | Este archivo | — | — |

## Lecciones

| # | Lección | Acción sugerida |
|---|---|---|
| 1 | Confirmar contra `hallazgo.md` (paso 3) atrapa las falsas alarmas: un cambio detectado no es un cambio real hasta reproducirlo | Mantener el paso 3 como obligatorio |
| 2 | El Python local es **3.6**: no existen `capture_output` ni `str.isascii` | Todo script o comando del incidente debe ser compatible con 3.6 |
| 3 | En zsh, un comando guardado en una variable (`Q="python3 …"`) no se divide en palabras | Usar funciones de shell (`q(){ python3 -I herramientas/q.py "$@"; }`) |
| 4 | El plan no tiene una herramienta para repetir `ejemplos.jsonl`; se resolvió con un script en línea | Si se repite, crear una herramienta nueva para eso |
| 5 | `q.py` exige la conclusión antes de ver la respuesta; en el paso 5 se reescribió después, en el archivo nuevo | Para exploración real: correr el request y luego anotar la conclusión real |
| 6 | La detección completa cuesta 46 requests y ~30 s | Cada 15 min hasta las 20:00 ≈ 830 requests: cabe en el presupuesto |
