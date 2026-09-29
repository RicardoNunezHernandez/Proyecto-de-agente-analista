# Análisis de la evaluación · Parte F

**Estado:** parcial. P01 a P04 ya se corrieron con el modelo real (`gemini-3.6-flash`) el
28 de septiembre. P05 se cortó por cuota agotada y P06 a P10 quedan pendientes de la
corrida del día siguiente. Todo lo marcado como *pendiente* se llena con
`python -m app.evaluar logs/corrida-*.jsonl`, que imprime la tabla y escribe
`evaluacion/resultados.json`.

---

## 1. Las diez preguntas

| ID | Resultado | Turnos | Herramientas | Cifras sin respaldo | Nota |
|---|---|---|---|---|---|
| P01 | PASA (7184) | 2 | 1 | `[]` | Una sola llamada a `contar`, sin búsqueda previa: la pregunta no pide un giro |
| P02 | PASA (184) | 3 | 2 | `[]` | `buscar_actividades("cafeteria")` y `contar(codigo_act="722515")`: los tres giros son una sola clase SCIAN |
| P03 | PASA (685, 387, 296, 250, 167) | 2 | 1 | `[]` | Un solo `ranking(por="codigo_act", top=5)`; 53.6 s, la más lenta por lo larga que es la respuesta |
| P04 | PASA (154, 118, 36) | 3 | 2 | `[]` | `buscar_actividades` y `ranking`; el total salió de `total_filtrado`, sin llamar a `contar` |
| P05 | *pendiente* (cortada por cuota) | — | 1 | — | Alcanzó a pedir `buscar_actividades("taqueria")` antes del 429 |
| P06 | *pendiente* | | | | |
| P07 | *pendiente* | | | | |
| P08 | *pendiente* | | | | |
| P09 | *pendiente* · manual | | | | juicio contra el criterio, con la frase de la respuesta que lo justifica |
| P10 | *pendiente* · manual | | | | idem |

Las cuatro respondidas coinciden exactamente con las cifras de `evaluacion/esperadas.json`,
calculadas con pandas antes de la corrida.

## 2. Totales

- Automáticas aprobadas: **4 de 4 corridas** (faltan 4 de las 8 automáticas).
- Manuales: pendientes.
- Llamadas reales al modelo hasta ahora: **16** (5 de una prueba desde la terminal y 11 del
  lote, contando la que se cortó).
- Respuestas en las que la guardia intervino: **0 de 5**. Las cinco revisiones salieron con
  `cifras_sin_respaldo: []`.

## 3. Tres casos analizados

### Caso 1 · La misma pregunta, de 5 turnos a 3 (causa: la declaración y el prompt)

La primera pregunta real fue «¿Cuántas farmacias hay en Tampico?» desde la terminal, y gastó
**5 turnos y 4 herramientas**: llegó al cierre forzado. La bitácora
(`logs/corrida-20260928-233558.jsonl`) muestra por qué:

```
buscar_actividades {"texto": "farmacia"}      -> devolvió 464111 y 464112
buscar_actividades {"texto": "medicamentos"}  -> sobraba: ya tenía las clases
contar  {"municipio": "Tampico", "codigo_act": "464111,464112"}   -> 154
ranking {"municipio": "Tampico", "codigo_act": "464111,464112", "por": "codigo_act"}
```

Dos llamadas de más. La segunda búsqueda fue el modelo asegurándose «por si acaso», y el
`contar` fue innecesario porque `ranking` ya devuelve `total_filtrado`: el 154 venía incluido
en la cuarta llamada.

**Causa:** el prompt de sistema y la descripción de la declaración. El prompt decía «si no
encuentras nada, prueba con un sinónimo» sin aclarar que eso aplica **sólo** cuando la lista
vuelve vacía, y ninguna de las dos decía que `ranking` trae el total y el desglose juntos.

**Qué se cambió:** tres renglones del prompt (una sola búsqueda salvo lista vacía; `ranking`
da total y desglose en una llamada; la mayoría de las preguntas se resuelven con dos
herramientas) y la descripción de `ranking` en `DECLARACIONES`.

**Resultado medido:** P04 del banco es exactamente la misma pregunta de farmacias, y con el
prompt corregido la resolvió en **3 turnos y 2 herramientas**, con la misma respuesta
(154 = 118 + 36). De 5 llamadas a 3 en la misma pregunta: el gasto estimado del banco bajó de
unas 50 llamadas a unas 30, bajo una cuota de 20 al día.

### Caso 2 · P05 cortada por cuota (causa: el modelo, no el agente)

P05 alcanzó a pedir `buscar_actividades("taqueria")` y en la siguiente llamada recibió
`429 RESOURCE_EXHAUSTED`, con `quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier`
y `quotaValue: 20`: el tope diario de la capa gratuita para `gemini-3.6-flash`.

No es un fallo del agente ni de las herramientas. Lo que sí demuestra es que el lote hace lo
que debe: registró un evento `error` en la bitácora, siguió su curso y terminó informando
`4 respondidas, 1 con error`, sin tumbar el programa ni perder las cuatro respuestas ya
obtenidas.

**Qué cambiaría:** repartir la corrida desde el principio en tramos de cuatro o cinco
preguntas por día, y no gastar llamadas reales en pruebas que el modelo simulado resuelve
igual. Las 5 llamadas del caso 1 fueron, en los hechos, una quinta parte de la cuota del día
gastada en una pregunta que el banco volvía a hacer.

### Caso 3 · *pendiente de la corrida de P05 a P10*

## 4. ¿La guardia corrigió alguna respuesta?

**Todavía no.** Las cinco revisiones de las respuestas reales salieron con
`cifras_sin_respaldo: []`: ninguna trajo una cifra que no viniera de una herramienta. Vale la
pena notar que las respuestas sí traen bastantes números —P03 menciona cinco totales y cinco
códigos SCIAN de seis dígitos, P04 menciona 154, 118, 36 y las clases 464111 y 464112— y
todos estaban respaldados.

Que no se active es el resultado deseado, no una falla de la guardia: el prompt pide no
calcular y el modelo obedeció. Lo que la habría activado es exactamente lo que el modelo no
hizo: sumar dos subtotales en vez de pedirlos, calcular la diferencia entre dos municipios o
sacar un porcentaje. Los casos G2 y G3 de `traza_manual.md` son esa situación con las cifras
reales de taquerías, y la guardia los detecta.

Con el modelo simulado sí se activa, y ese camino está probado de punta a punta: en el paso 3
del guion escribe «160 farmacias» cuando `contar` devolvió 154, la guardia lo detecta, el
ciclo manda el mensaje de corrección —que gasta un turno— y el paso 4 responde con la cifra
respaldada (comprobaciones 59 a 69 de `pruebas/prueba_herramientas.py`).

## 5. Qué hace el modelo y qué hace mi código

El **modelo** hace tres cosas y ninguna más: interpreta la pregunta en español, elige cuál de
las cuatro herramientas pedir y con qué argumentos, y al final redacta la respuesta en
palabras. Nunca ve los 22900 renglones del DENUE: sólo ve la descripción de las herramientas
y los resultados que el programa le devuelve.

El **código** hace todo lo demás: arma y reenvía el historial completo en cada turno (el
modelo no tiene memoria), ejecuta la herramienta pedida contra el `DataFrame` de pandas,
cuenta y ordena las filas, impone el presupuesto de 5 turnos y 6 herramientas con cierre
forzado en modo `NONE`, convierte cualquier argumento inválido en un error estructurado que el
modelo pueda corregir, verifica con `cifras_sin_respaldo` que cada número de la respuesta
venga de la pregunta o de una herramienta, y escribe la bitácora.

En una frase: **el modelo decide qué preguntar y cómo decirlo; el código decide qué es
verdad.** La exactitud no depende de que el modelo «sea bueno con números», porque no se le
permite hacer ninguna cuenta: los totales los produce pandas y la guardia comprueba que la
redacción no haya agregado ninguna cifra que nadie contó.
