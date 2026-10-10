# Plan de incidente — Cambio del servicio (≈15:30)

**Objetivo:** el clon se evalúa contra la versión del original vigente a las 20:00. Hay que detectar rápido qué cambió, medirlo y adaptarnos.

## 1. Antes de las 15:30 (preparación)

1. **Seq de humo con línea base.** Un archivo con ~40 requests que cubren:
   - los 16 errores;
   - cada comando;
   - el control, incluido PING;
   - strikes y límite de 100000;
   - `sugerencia`;
   - rutas y auth.

   Correrla ahora contra el original y guardar las respuestas como **línea base**.
2. **Script de comparación.** Corre la seq de humo y muestra solo lo que cambió (*antes → después*). Un comando, menos de 1 minuto.
3. **Clon con todo lo variable en config:** orden de los filtros, textos del catálogo, fórmula del control (D25), límite de 100000 y umbral de strikes.
4. **Herramientas listas:** `sweep.py` y el buscador de fórmulas, por si cambia el control.
5. **Presupuesto:** quedan ~6.800 de 8.000 requests.

## 2. Desde las 15:30 (detección)

6. **Correr la seq de humo cada ~15 minutos** hasta ver una diferencia. No sabemos la hora exacta del cambio.
7. **Clasificar el cambio:**

| Si cambia… | Cómo se ve en la comparación | Qué tocamos |
|---|---|---|
| Un texto o un status | Mismo error, cuerpo distinto | Catálogo (config) |
| El orden de validación | Otro error gana | Orden del pipeline (config) |
| La fórmula del control | Controles conocidos dan E202 | Validador (config o una función) + `sweep.py` |
| Un límite o umbral | 100000 o 3 strikes se comportan distinto | Config |
| Un comando nuevo | Uno que daba E301 ahora responde | Código nuevo (lo más caro) |
| Una regla de estado | Saldos, IDs o bloqueos distintos | Código del motor |

## 3. Después de detectarlo (adaptación)

8. **Explorar el cambio** con un sub-agente. Usar seqs nuevas en `experimentos.jsonl`, que empiecen con reset, para que la spec pueda citarlas en «Cambios durante el día».
9. **Copiar la versión nueva**, que es la que rige a las 20:00. En la spec, marcar las líneas viejas que ya no aplican como «versión mañana».
10. **Ajustar el clon → replay → deploy.**
    - El replay del log viejo va a fallar en lo que cambió, y eso es esperado.
    - Hay que separar el replay en «versión mañana» y «versión tarde».
11. **Re-chequeo final antes de las 20:00:** volver a correr la seq de humo, por si hubo un segundo cambio.

## 4. Registro

Durante el incidente, llenar `INCIDENT.md` con:
- hora;
- síntoma;
- cómo se detectó (ids del log);
- causa;
- qué se cambió en el clon.
