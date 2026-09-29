# Análisis de la evaluación · Parte F

**Estado:** pendiente de la corrida con el modelo real. Las secciones 1 a 4 se llenan con lo
que produzca el programa; la sección 5 no depende de la corrida y ya está escrita.

Para llenarlo:

```bash
python -m evaluacion.calcular_esperadas          # commit ANTES de la primera corrida real
python -m app.lote --desde P01 --hasta P05       # día 1
python -m app.lote --desde P06 --hasta P10       # día 2
python -m app.evaluar logs/corrida-*.jsonl       # imprime la tabla y escribe resultados.json
```

`app.evaluar` imprime exactamente las columnas de la tabla 1 y guarda todo en
`evaluacion/resultados.json`, de donde se copian las cifras aquí.

---

## 1. Las diez preguntas

| ID | Resultado | Turnos | Herramientas | Cifras sin respaldo | Nota |
|---|---|---|---|---|---|
| P01 | | | | | |
| P02 | | | | | |
| P03 | | | | | |
| P04 | | | | | |
| P05 | | | | | |
| P06 | | | | | |
| P07 | | | | | |
| P08 | | | | | |
| P09 | manual | | | | juicio contra el criterio, con la frase de la respuesta que lo justifica |
| P10 | manual | | | | idem |

## 2. Totales

- Automáticas aprobadas: **_ de 8**
- Manuales aprobadas (juicio propio contra el criterio): **_ de 2**
- Llamadas totales al modelo: **_** (la suma de los eventos `modelo` de las bitácoras reales)
- Respuestas en las que la guardia intervino: **_**

## 3. Tres casos analizados

Para cada uno: la pregunta, qué pidió el modelo (de la bitácora), qué salió mal o por qué
gastó más herramientas, y la causa entre estas seis: **la herramienta**, **la descripción de
la declaración**, **el prompt de sistema**, **el modelo**, **la guardia** o **la esperada mal
calculada**. Cerrar con qué se cambiaría.

1. **Caso 1 —**
2. **Caso 2 —**
3. **Caso 3 —**

## 4. ¿La guardia corrigió alguna respuesta?

Se llena con las bitácoras reales: hay corrección cuando un evento `guardia` trae
`cifras_sin_respaldo` no vacío y el siguiente evento `modelo` es de un turno posterior.

Lo que ya se sabe sin el modelo real: con el modelo simulado la guardia **sí** interviene, y
es el caso que hay que buscar en la corrida real. En el paso 3 del guion el simulado escribe
«En Tampico hay 160 farmacias» y `contar` había devuelto otro número, así que
`cifras_sin_respaldo` sale `[160]`, el ciclo manda el mensaje de corrección de la sección 8.3
—que gasta un turno— y el paso 4 responde con la cifra que sí vino de la herramienta. Está
comprobado en `pruebas/prueba_herramientas.py` (comprobaciones 59 a 65) y detallado en
`traza_manual.md`, E.1.

Si en la corrida real no se activa, lo que la habría activado es exactamente eso: que el
modelo sumara dos subtotales, calculara un porcentaje o una diferencia en lugar de pedir el
total a `contar`. Los casos G2 y G3 de la traza E.2 son esa situación con cifras reales.

## 5. Qué hace el modelo y qué hace el código

El **modelo** hace tres cosas y ninguna más: interpreta la pregunta en español, elige cuál de
las cuatro herramientas pedir y con qué argumentos, y al final redacta la respuesta en
palabras. Nunca ve los 22,900 renglones del DENUE: sólo ve la descripción de las herramientas
y los resultados que el programa le devuelve.

El **código** hace todo lo demás: arma y reenvía el historial completo en cada turno (el
modelo no tiene memoria), ejecuta la herramienta pedida contra el `DataFrame` de pandas,
cuenta y ordena las filas, impone el presupuesto de 5 turnos y 6 herramientas con cierre
forzado en modo `NONE`, convierte cualquier argumento inválido en un error estructurado que
el modelo pueda corregir, verifica con `cifras_sin_respaldo` que cada número de la respuesta
venga de la pregunta o de una herramienta, y escribe la bitácora.

En una frase: **el modelo decide qué preguntar y cómo decirlo; el código decide qué es
verdad.** La exactitud no depende de que el modelo «sea bueno con números», porque no se le
permite hacer ninguna cuenta: los totales los produce pandas y la guardia comprueba que la
redacción no haya agregado ninguna cifra que nadie contó.
