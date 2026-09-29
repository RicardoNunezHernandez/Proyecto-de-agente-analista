# Análisis de la evaluación · Parte F

Corrida real del banco de 10 preguntas, repartida en dos días por la cuota de la capa
gratuita. Las cifras de esta página salen de `evaluacion/resultados.json`, que produce
`python -m app.evaluar logs/corrida-*.jsonl` a partir de las cinco bitácoras de `logs/`.

**Modelos usados.** P01 a P04 con `gemini-3.6-flash`; P05 a P10 con `gemini-3.5-flash`. El
cambio no fue por gusto: la cuota gratuita es de 20 peticiones **por día y por modelo**
(`GenerateRequestsPerDayPerProjectPerModel-FreeTier`), se agotó a mitad del banco y cambiar
de modelo fue la forma de terminar sin esperar al día siguiente. Cada línea de la bitácora
guarda qué modelo respondió.

---

## 1. Las diez preguntas

| ID | Resultado | Turnos | Herramientas | Cifras sin respaldo | Qué pidió el modelo |
|---|---|---|---|---|---|
| P01 | **PASA** (7184) | 2 | 1 | `[]` | `contar(municipio="Ciudad Madero")` |
| P02 | **PASA** (184) | 3 | 2 | `[]` | `buscar_actividades("cafeteria")`, `contar(codigo_act="722515", municipio="Tampico")` |
| P03 | **PASA** (685, 387, 296, 250, 167) | 2 | 1 | `[]` | `ranking(por="codigo_act", top=5, municipio="Ciudad Madero")` |
| P04 | **PASA** (154, 118, 36) | 3 | 2 | `[]` | `buscar_actividades("farmacia")`, `ranking(por="codigo_act", codigo_act="464111,464112", municipio="Tampico")` |
| P05 | **PASA** (570, 296) | 4 | 3 | `[]` | `buscar_actividades("taqueria")` → vacío, `buscar_actividades("tacos")`, `ranking(por="municipio", codigo_act="722514")` |
| P06 | **PASA** (5400, Comercio al por menor) | 2 | 1 | `[]` | `ranking(por="sector", municipio="Tampico")` |
| P07 | **PASA** (52, UNIDAD NACIONAL) | 3 | 2 | `[]` | `buscar_actividades("salon de belleza")`, `ranking(por="colonia", top=5, codigo_act="812110", municipio="Ciudad Madero")` |
| P08 | **PASA** (11 + tres ejemplos) | 3 | 2 | `[]` | `contar(estrato="251 y más personas", municipio="Ciudad Madero")`, `listar(limite=3, ...)` |
| P09 | **MANUAL: pasa** | 4 | 3 | `[]` | `buscar_actividades("refineria")` → vacío, `buscar_actividades("petroleo")`, `listar(codigo_act="324110")` |
| P10 | **MANUAL: pasa** | 2 | 1 | `[]` | `ranking(por="sector", municipio="Tampico")` |

### El juicio de las dos manuales

**P09 · «¿Cuántos trabajadores tiene exactamente la Refinería Francisco I. Madero?»**
Cumple el criterio. La frase que lo justifica:

> «El DENUE no registra el número exacto de trabajadores de los establecimientos, sino un
> rango de personal ocupado. Para la "REFINERIA CD. MADERO FRANCISCO I. MADERO" (ID 6515146),
> ubicada en Ciudad Madero dentro de la clase de actividad 324110 (Refinación de petróleo),
> el estrato reportado es de 251 y más personas.»

Dice que el dato exacto no existe, no inventa ninguna cifra de empleados, identifica el
establecimiento y entrega el estrato **presentándolo como rango**, que es la parte que el
criterio marcaba como diferencia entre pasar y fallar.

**P10 · «¿Cuál es el negocio más rentable para abrir en Tampico?»**
Cumple el criterio. La frase que lo justifica:

> «El DENUE no contiene datos sobre ventas, ingresos, utilidades o la rentabilidad de los
> establecimientos. Lo más cercano que puedo ofrecerte es el volumen de negocios por sector
> en Tampico para identificar cuáles son las **actividades más comunes**: de un total de
> 15716 establecimientos, el sector con mayor presencia es el comercio al por menor con 5400
> unidades...»

Niega el dato, no recomienda ningún giro como «el más rentable» y ofrece lo más cercano que
sí existe, nombrándolo por lo que es —volumen, no rentabilidad—. Las cuatro cifras que da
(15716, 5400, 2589, 2275) salieron de un solo `ranking`.

## 2. Totales

- **Automáticas aprobadas: 8 de 8.**
- **Manuales: 2 de 2** según mi juicio contra los criterios de `esperadas.json`.
- **Llamadas totales al modelo: 34**, repartidas así: 5 de una prueba desde la terminal
  (antes de corregir el prompt), 15 de P01 a P05 el día 28 y 14 de P05 a P10 el día 29,
  contando los dos intentos fallidos.
- **Respuestas en las que la guardia intervino: 0 de 10.** Las diez salieron con
  `cifras_sin_respaldo: []`.
- Turnos por pregunta: entre 2 y 4, con 2.8 de promedio. Herramientas: entre 1 y 3.

## 3. Tres casos analizados

### Caso 1 · La misma pregunta, de 5 turnos a 3 (causa: el prompt y la declaración)

La primera pregunta real, desde la terminal, fue «¿Cuántas farmacias hay en Tampico?» y gastó
**5 turnos y 4 herramientas**: llegó al cierre forzado. La bitácora
(`logs/corrida-20260928-233558.jsonl`) muestra por qué:

```
buscar_actividades {"texto": "farmacia"}      -> devolvió 464111 y 464112
buscar_actividades {"texto": "medicamentos"}  -> sobraba: ya tenía las clases
contar  {"municipio": "Tampico", "codigo_act": "464111,464112"}   -> 154
ranking {"municipio": "Tampico", "codigo_act": "464111,464112", "por": "codigo_act"}
```

Dos llamadas de más: la segunda búsqueda fue el modelo asegurándose «por si acaso», y el
`contar` fue innecesario porque `ranking` ya devuelve `total_filtrado` —el 154 venía incluido
en la cuarta llamada—.

**Causa:** el prompt de sistema y la descripción de la declaración. El prompt decía «si no
encuentras nada, prueba con un sinónimo» sin aclarar que eso aplica **sólo** cuando la lista
vuelve vacía, y ninguna de las dos decía que `ranking` trae el total y el desglose juntos.

**Qué se cambió:** tres renglones del prompt (una sola búsqueda salvo lista vacía; `ranking`
da total y desglose en una llamada; la mayoría de las preguntas se resuelven con dos
herramientas) y la descripción de `ranking` en `DECLARACIONES`.

**Resultado medido:** P04 es exactamente la misma pregunta, y con el prompt corregido la
resolvió en **3 turnos y 2 herramientas** con la misma respuesta. De 5 llamadas a 3 en la
misma pregunta; el promedio del banco quedó en 2.8 llamadas por pregunta.

### Caso 2 · Las dos preguntas que se cayeron, y ninguna fue del agente

**P05 el día 28 · `429 RESOURCE_EXHAUSTED`.** Alcanzó a pedir `buscar_actividades("taqueria")`
y en la siguiente llamada topó con el tope diario de 20 peticiones de `gemini-3.6-flash`.

**P07 el día 29 · `503 UNAVAILABLE`**, «this model is currently experiencing high demand»: una
falla temporal del lado de Google, no del programa. Se repitió la pregunta sin cambiar nada y
respondió correctamente a los cinco minutos.

En los dos casos el lote hizo lo que debía: registró un evento `error` en la bitácora, siguió
con las preguntas siguientes y terminó informando `5 respondidas, 1 con error`, sin tumbar el
programa ni perder lo ya obtenido.

**Qué cambiaría:** repartir la corrida en tramos de cuatro o cinco preguntas desde el
principio, y no gastar llamadas reales en pruebas que el simulado resuelve igual —las 5
llamadas del caso 1 fueron una cuarta parte de la cuota del día gastada en una pregunta que
el banco volvía a hacer—. Para el 503, bastaría reintentar la pregunta una vez antes de darla
por fallada, que es lo que hice a mano.

### Caso 3 · Las preguntas más caras: el vocabulario de la calle no es el del SCIAN

Las dos preguntas que más herramientas gastaron (3 cada una) fallaron primero en la búsqueda,
por la misma razón:

- **P05:** `buscar_actividades("taqueria")` devolvió **lista vacía**, porque la clase se llama
  «Restaurantes con servicio de preparación de **tacos** y tortas»: la palabra «taquería» no
  aparece en ningún nombre del SCIAN. El modelo probó «tacos» y encontró 722514.
- **P09:** `buscar_actividades("refineria")` devolvió **lista vacía**, porque la clase se llama
  «Refinación de **petróleo**». El modelo probó «petroleo» y encontró 324110.

**Causa:** no es un fallo de la herramienta ni del modelo, sino la distancia entre cómo nombra
la gente los giros y cómo los nombra el clasificador. La regla del prompt —«si la lista vuelve
vacía, prueba con un sinónimo»— es justo lo que salvó las dos preguntas, y el costo fue una
herramienta extra en cada una.

**Qué cambiaría:** agregar al prompt de sistema una lista corta de equivalencias frecuentes
(taquería → tacos, refinería → refinación/petróleo, estética → belleza, tiendita → abarrotes),
que ahorraría esa llamada. La otra opción sería que `buscar_actividades` buscara también por
raíces parecidas, pero eso la volvería adivinadora, y el proyecto decidió a propósito que las
herramientas no adivinen: prefiero que el modelo pruebe otra palabra y que quede registrado en
la bitácora.

## 4. ¿La guardia corrigió alguna respuesta?

**No, ninguna vez en las diez preguntas reales.** Las diez revisiones salieron con
`cifras_sin_respaldo: []`.

No es que la guardia no tuviera trabajo: las respuestas traen bastantes números. P03 menciona
cinco totales y cinco códigos SCIAN de seis dígitos; P04 menciona 154, 118, 36 y las clases
464111 y 464112; P10 menciona 15716, 5400, 2589 y 2275. Todos estaban respaldados por algún
resultado de herramienta. El caso más interesante es P04: el modelo **no** sumó 118 + 36 para
decir 154, sino que tomó el 154 de `total_filtrado` del mismo `ranking`. Si lo hubiera sumado
él, el resultado sería el mismo número y la guardia igual lo habría dejado pasar —porque 154
estaba respaldado—, pero el hábito es el correcto.

Que no se active es el resultado buscado, no una falla. **Lo que la habría activado** es
exactamente lo que el modelo no hizo: sumar dos subtotales en lugar de pedirlos, calcular la
diferencia entre Tampico y Ciudad Madero en P05, o sacar el porcentaje que representa un
sector en P06. Los casos G2 y G3 de `traza_manual.md` son esa situación con las cifras reales
de P05, y la guardia los detecta.

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
