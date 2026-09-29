# Traza · Parte E

**Proyecto:** Agente analista del DENUE · ACD-2504 · Unidad 1
**Autor:** Ricardo Núñez Hernández

> **Cómo se produjo este documento.** El profesor autorizó de forma expresa que todo el
> proyecto, incluida esta parte, se desarrollara con asistencia de inteligencia artificial.
> Las predicciones de cada tabla se derivaron leyendo el código de `app/herramientas.py`,
> `app/agente.py` y `app/guardia.py`; después se ejecutaron los mismos casos para comparar.
> Cada sección indica el comando que reproduce lo ejecutado, así que cualquier cifra de aquí
> se puede volver a obtener.

E.1 se corrió con el archivo completo (`data/denue_tampico_madero.csv`, 22900
establecimientos) y E.3 con la tabla de 8 filas del docente (`data/mini_denue.csv`), que es
la que corresponde a cada caso.

---

## E.1 · El ciclo con el simulado

**Pregunta:** «¿Cuántas farmacias hay en Tampico?»
**Condiciones:** modelo simulado recién creado, `MAX_TURNOS = 5`, `MAX_HERRAMIENTAS = 6`.

### Predicción, leyendo el código

`responder` mete la pregunta al historial y entra al ciclo. El simulado avanza un paso por
llamada: paso 1 pide `buscar_actividades`, paso 2 pide `contar`, paso 3 redacta con una
cifra inventada (160) y paso 4 redacta 154. La guardia debe detener el paso 3, porque 160 no
está ni en la pregunta ni en los resultados; esa corrección gasta un turno. Como `contar`
sobre el archivo completo devuelve 154, la respuesta del paso 4 sí debe quedar respaldada.
Predicción: termina en el turno 4, con 2 herramientas y sin cifras sin respaldo.

### Lo ejecutado

| Turno | Mensajes en el historial al llamar | Qué devuelve el modelo | Qué hace el código | Usadas | Eventos |
|---|---|---|---|---|---|
| 1 | 1 | Pide `buscar_actividades(texto="farmacia")`, id `sim-1` | Ejecuta la herramienta, agrega el turno del modelo tal como llegó y un mensaje con la `function_response` del mismo id | 1 | `modelo`, `herramienta` |
| 2 | 3 | Pide `contar(codigo_act="464111,464112", municipio="Tampico")`, id `sim-2` | Ejecuta `contar`, que devuelve `total 154`; agrega turno del modelo y `function_response` | 2 | `modelo`, `herramienta` |
| 3 | 5 | Texto: «Respuesta: En Tampico hay 160 farmacias.» | La guardia detecta `[160]`: primera y única corrección, agrega el mensaje de la sección 8.3 al historial y sigue | 2 | `modelo`, `guardia` |
| 4 | 7 | Texto: «Respuesta: En Tampico hay 154 farmacias (clases 464111 y 464112).» | La guardia no encuentra cifras sin respaldo: entrega la respuesta | 2 | `modelo`, `guardia`, `fin` |

`forzar_texto` fue `false` en los cuatro turnos: nunca se llegó al turno 5 ni se agotó el
presupuesto de herramientas.

Secuencia completa de eventos de la bitácora:

```
inicio, modelo, herramienta, modelo, herramienta, modelo, guardia, modelo, guardia, fin
```

Devuelto por `responder`: `turnos = 4`, `herramientas = 2`, `cifras_sin_respaldo = []`,
`segundos = 0.03`. Coincide con la predicción en todo.

### Las tres preguntas de cierre

**(1) ¿Cuántos mensajes tiene el historial al terminar?** **Ocho.** En orden: la pregunta;
el turno del modelo del turno 1; el mensaje con la `function_response` de
`buscar_actividades`; el turno del modelo del turno 2; el mensaje con la `function_response`
de `contar`; el turno del modelo del turno 3 (el texto con 160); el mensaje de corrección de
la guardia; y el turno del modelo del turno 4. Al llamar en el turno 4 había 7 y después se
agregó el contenido del modelo: 8.

**(2) ¿Qué total devolvió `contar` y por qué la guardia marcó la respuesta del turno 3?**
`contar(codigo_act="464111,464112", municipio="Tampico")` devolvió **154**, que es la suma de
las 118 farmacias sin minisúper y las 36 con minisúper (clases 464111 y 464112) —y esa suma
la hizo pandas contando filas, no el modelo. La guardia marcó el turno 3 porque el simulado
escribió **160**, y 160 no aparece ni en la pregunta ni en ningún resultado de las
herramientas: es una cifra inventada con apariencia exacta, justo lo que la guardia existe
para atrapar. En el turno 4 el texto trae 154, 464111 y 464112, y las tres cifras sí están en
los resultados, así que `cifras_sin_respaldo` quedó vacía y la respuesta salió sin aviso.

Una comprobación extra que ayuda a entender la guardia: si el mismo ciclo se corre contra la
tabla de 8 filas, `contar` devuelve **1** y entonces **también** el 154 del paso 4 queda sin
respaldo. La respuesta se entrega con el aviso pegado:

```
[Aviso] Cifras sin respaldo en los datos: [154]
```

Es decir, la guardia no compara contra lo que «debería» ser cierto en el mundo: compara
contra lo que devolvieron *estas* herramientas en *esta* pregunta. Con otros datos, la misma
respuesta del modelo pasa de correcta a marcada.

**(3) La misma traza con `MAX_HERRAMIENTAS = 1`.** Termina **en el turno 2**, con **1
herramienta** usada, y responde el texto de cierre forzado:

```
Respuesta: No pude completar la consulta con el presupuesto.
```

Por qué: en el turno 1 se ejecuta `buscar_actividades` y `usadas` llega a 1, que ya iguala el
presupuesto, así que el código pone `forzar_texto = true`. En el turno 2 `llamar_modelo` usa
el modo `NONE` —prohibido pedir herramientas— y el simulado, por su regla adicional, devuelve
el texto de presupuesto agotado en lugar de la petición del paso 2. La guardia no encuentra
cifras en ese texto, así que `cifras_sin_respaldo` queda vacía y el ciclo cierra.
Eventos: `inicio, modelo, herramienta, modelo, guardia, fin`. Historial final: 4 mensajes.

Comprobado con el programa (comprobaciones 59 a 69 de `pruebas/prueba_herramientas.py`) y con:

```bash
python -m app.cli "¿Cuántas farmacias hay en Tampico?" --simulado
```

---

## E.2 · La guardia

**Pregunta:** «¿Dónde hay más taquerías, en Tampico o en Ciudad Madero? Dame la cifra de cada
municipio.»

De la pregunta, `numeros` no saca ninguna cifra. De los dos resultados de herramientas,
`numeros_en` saca `{866, 722514, 570, 296, 5, 2026}`: el 5 y el 2026 vienen del texto de la
fuente, «DENUE 05/2026, INEGI».

| Caso | `numeros(respuesta)` | `cifras_sin_respaldo` | Por qué |
|---|---|---|---|
| **G1** Tampico tiene 570 taquerías y Ciudad Madero 296. | `{570, 296}` | `[]` | Las dos cifras salieron del `ranking`. |
| **G2** Tampico tiene 570 y Madero 296: una diferencia de 274. | `{570, 296, 274}` | `[274]` | 570 − 296 lo calculó el modelo; ninguna herramienta devolvió 274. |
| **G3** En total hay 866; Tampico concentra el 65.8 %. | `{866, 65.8}` | `[65.8]` | 866 sí está en los resultados; el porcentaje lo calculó el modelo. |
| **G4** `1. Tampico: 570` / `2. Ciudad Madero: 296` / Clase SCIAN 722514, DENUE 05/2026. | `{570, 296, 722514, 5, 2026}` | `[]` | Las marcas de lista «1. » y «2. » se borran antes de buscar cifras, así que el 1 y el 2 del inciso no cuentan; el 5 y el 2026 vienen de la fuente. |
| **G5** Tampico tiene 1,570 taquerías. | `{1570}` | `[1570]` | La coma de miles se interpreta bien (1570, no 1 y 570) y esa cifra no existe en los resultados. |
| **G6** Ciudad Madero tiene 570 taquerías y Tampico 296. | `{570, 296}` | `[]` | Las dos cifras existen en los resultados. **La guardia la deja pasar.** |

Ejecutado y comparado: coincide caso por caso (comprobaciones 51 a 56).

### Pregunta de cierre: ¿cuál respuesta falsa pasa la guardia?

**G6.** Dice que Ciudad Madero tiene 570 y Tampico 296, cuando el `ranking` devolvió lo
contrario (y el archivo real confirma Tampico 570, Madero 296). **Por qué no la detecta:** la
guardia sólo comprueba la *procedencia* de cada cifra —que el número aparezca en la pregunta
o en los resultados—, no la *correspondencia* entre la cifra y la etiqueta a la que se pega.
Para `cifras_sin_respaldo`, `{570, 296}` está respaldado y ahí termina su trabajo. Es una
guardia de invención, no de asignación.

**Qué sí la detecta:** la evaluación de la Parte F, cuando la esperada ata cada cifra a su
nombre. Ojo: la esperada de P05 en `evaluacion/esperadas.json` tiene
`cifras_clave: [296, 570]` y `textos_clave: ["Tampico", "Ciudad Madero"]`, y **G6 también
pasaría** ese criterio, porque los cuatro elementos aparecen en el texto. Para atrapar el
intercambio habría que exigir la pareja, por ejemplo `textos_clave: ["Tampico tiene 570"]`, o
revisarlo a mano al escribir `analisis.md`. Dicho de frente: contra un error de asignación el
proyecto no tiene un detector automático completo; lo que queda es la esperada escrita con el
par cifra-etiqueta y la revisión humana. Ésa es la diferencia entre verificar que nadie
inventó un número y verificar que el número dice la verdad.

---

## E.3 · Las herramientas sobre la tabla pequeña

`data/mini_denue.csv`, 8 filas ficticias con las mismas columnas del DENUE. Predicción a mano
y después ejecución con:

```bash
python -c "from app.herramientas import *; d,s = cargar_datos('data/mini_denue.csv','data/sectores_scian.csv'); h = Herramientas(d,s); print(h.contar(municipio='tampico'))"
```

| Caso | Predicción a mano | Ejecutado | ¿Coincide? |
|---|---|---|---|
| **H1** `contar(municipio="tampico")` | Filas 1, 3, 4, 6, 8 → `total 5`, `filtros {municipio: "Tampico"}` | `total 5`, municipio corregido a `Tampico` | Sí |
| **H2** `contar(codigo_act="4641")` | Prefijo: 464111 (filas 1, 7), 464112 (fila 2), 464113 (fila 3) → `total 4` | `total 4` | Sí |
| **H3** `contar(codigo_act="464111,464112", municipio="Ciudad Madero")` | Filas 2 y 7 → `total 2` | `total 2` | Sí |
| **H4** `ranking(por="colonia", top=2, municipio="Tampico")` | CENTRO 3 (filas 1, 3, 6), LAS AMERICAS 2 (filas 4, 8); `total_filtrado 5` | `[{CENTRO, 3}, {LAS AMERICAS, 2}]`, `total_filtrado 5` | Sí |
| **H5** `listar(limite=2, codigo_act="7225")` | Filas 4, 5, 6 → `total 3`; del estrato mayor al menor: TAQUERIA DOÑA LUPE (11 a 30), CAFE DEL PUERTO (6 a 10) → `mostrados 2` | Los dos en ese orden, `total 3`, `mostrados 2` | Sí |
| **H6** `buscar_actividades("farmacias")` | «farmacias» → «farmacia»; 464111 con 2, 464112 con 1; 464113 (naturista) no contiene la palabra | `[{464111, 2}, {464112, 1}]`, `palabras ["farmacia"]` | Sí |
| **H7** `contar(colonia="centro", municipio="Ciudad Madero")` | En Madero de esta tabla no hay ninguna colonia CENTRO → `ok: false`, y como el municipio se filtra antes, tampoco hay colonias parecidas que sugerir | `ok: false`, `valores_validos: null` | Sí |

### Qué enseña H2 sobre los prefijos

Un prefijo agrupa por jerarquía SCIAN, no por giro: `4641` devolvió 4 y no 3 porque además de
las farmacias sin minisúper (464111) y con minisúper (464112) arrastró la clase 464113, de
productos naturistas y homeopáticos, que no es una farmacia. Por eso el prompt de sistema
obliga a llamar `buscar_actividades` primero y a armar el `codigo_act` con las clases exactas
del giro, en lugar de cortar el código a la primera rama que parezca cómoda.

Un detalle del archivo real que confirma lo mismo desde el otro lado: en `data/mini_denue.csv`
Ciudad Madero no tiene colonia CENTRO, pero en el DENUE completo sí existe y tiene 574
establecimientos. Las herramientas no adivinan ni con los prefijos ni con los nombres: piden
el valor exacto y, cuando no existe, sugieren los que sí.
