# Agente analista del DENUE · Tampico y Ciudad Madero

**Asignatura:** Desarrollo de Agentes Inteligentes (ACD-2504) · Unidad 1
**Proyecto:** Agente analista del DENUE · Grupo 850P-A · Semestre agosto–diciembre 2026
**Autor:** Ricardo Núñez Hernández

## Qué hace

Responde en español preguntas sobre los negocios de Tampico y Ciudad Madero —cuántas
farmacias hay, en qué colonia se concentran los salones de belleza, qué establecimientos
grandes existen— con cifras exactas tomadas del DENUE, desde la terminal o desde un bot de
Telegram.

## Por qué es un agente

El modelo **nunca ve los datos**. Sólo ve la descripción de cuatro herramientas. En cada
pregunta el programa hace un ciclo de **percibir → decidir → actuar → observar**:

1. **Percibe** la pregunta y, en cada vuelta, los resultados de las herramientas.
2. **Decide**: el modelo elige qué herramienta pedir y con qué argumentos.
3. **Actúa**: el código —no el SDK— ejecuta esa herramienta sobre un `DataFrame` de pandas.
4. **Observa**: el resultado vuelve al historial con el mismo `id` de la petición, y el
   ciclo repite hasta que el modelo redacta.

Todo dentro de un **presupuesto** (5 llamadas al modelo y 6 herramientas por pregunta, con
cierre forzado) y con una **guardia** que revisa por código cada cifra de la respuesta antes
de mostrarla. La ejecución automática de herramientas del SDK está **desactivada**: el
modelo sólo puede *pedir*.

## Los datos y su fuente

- **Fuente:** INEGI, *Directorio Estadístico Nacional de Unidades Económicas* (DENUE),
  edición **05/2026**, recorte de los municipios de Tampico y Ciudad Madero, Tamaulipas
  (22,900 establecimientos, 4.9 MB).
- Se publica bajo los [Términos de Libre Uso de la Información del INEGI](https://www.inegi.org.mx/inegi/terminos.html):
  puede usarse citando la fuente, y por eso **cada respuesta del agente la menciona**.
- Los archivos de `data/` los entrega el docente y **no se modifican**:
  `denue_tampico_madero.csv`, `sectores_scian.csv`, `diccionario_datos.md`,
  `mini_denue.csv`, `preguntas_prueba.json`.
- Se leen siempre con `dtype=str` y `keep_default_na=False`: si pandas convirtiera
  `codigo_act` en número, los prefijos SCIAN dejarían de funcionar.

## Arquitectura

```
terminal / Telegram
        |
        v
agente.responder(pregunta, herramientas, sistema, llamar, bitacora)
        |      ^                                   |
        |      | function_response (mismo id)      | evento por evento
        v      |                                   v
  modelo.llamar_modelo  ->  el modelo PIDE     logs/corrida-*.jsonl
        |                                          ^
        v                                          |
  agente.ejecutar  ->  herramientas.py (pandas)  --+
        |
        v
  guardia.cifras_sin_respaldo  ->  respuesta (o aviso)
```

### Las cuatro herramientas

| Herramienta | Recibe | Devuelve |
|---|---|---|
| `buscar_actividades` | `texto` | Hasta 15 clases SCIAN cuyo nombre contiene todas las palabras (de 3 letras o más, en singular), con su `codigo_act` y cuántos establecimientos tiene cada una en los dos municipios |
| `contar` | los cinco filtros | `total` de establecimientos que cumplen **todos** los filtros |
| `ranking` | `por`, `top` y filtros (sin `colonia`) | `filas` de `{valor, total}` de mayor a menor, más `actividad` si agrupa por `codigo_act`, `nombre_sector` si agrupa por `sector`, y `total_filtrado` |
| `listar` | `limite` y filtros (exige al menos uno) | `establecimientos` con `id, nombre, actividad, estrato, colonia, municipio`, del estrato mayor al menor y por nombre dentro del estrato |

Filtros comunes: `municipio`, `codigo_act` (uno o varios, separados por coma, cada uno como
**prefijo**), `sector`, `estrato` y `colonia`. Todo resultado correcto trae `ok: true`,
`fuente` y `filtros` con el valor ya corregido; todo error trae
`{"ok": false, "error": "...", "valores_validos": [...] | null}`.

## Instalación

```bash
git clone https://github.com/RicardoNunezHernandez/Proyecto-de-agente-analista.git
cd Proyecto-de-agente-analista
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
```

Después ponga en `.env` su clave de Google AI Studio y el token de su bot, y copie los
archivos de `material_proyecto_u1.zip` en `data/`. **El `.env` no se sube al repositorio.**

```
GEMINI_API_KEY=su_clave
GEMINI_MODEL=gemini-3.6-flash
TELEGRAM_BOT_TOKEN=su_token
TELEGRAM_USUARIOS_PERMITIDOS=123456789
```

## Cómo correr

```bash
# Una pregunta desde la terminal (con el modelo real)
python -m app.cli "¿Cuántas farmacias hay en Tampico?"

# Lo mismo sin gastar cuota, con el modelo simulado
python -m app.cli "¿Cuántas farmacias hay en Tampico?" --simulado

# El banco de preguntas, por tramos (la cuota gratuita alcanza ~20 llamadas al día)
python -m app.lote --simulado
python -m app.lote --desde P01 --hasta P05
python -m app.lote --desde P06 --hasta P10

# Las pruebas sin red
python -m pruebas.prueba_herramientas

# Las esperadas con pandas, ANTES de la primera corrida real
python -m evaluacion.calcular_esperadas

# La evaluación contra las esperadas
python -m app.evaluar logs/corrida-20260930-101500.jsonl logs/corrida-20260930-184500.jsonl

# El bot de Telegram
python -m app.bot --simulado
python -m app.bot
```

Cada corrida escribe `logs/corrida-AAAAMMDD-HHMMSS.jsonl`, una línea JSON por evento
(`inicio`, `modelo`, `herramienta`, `guardia`, `fin`, `error`).

## El bot de Telegram

1. En Telegram, abra `@BotFather` (la cuenta oficial, con palomita azul) y envíe `/newbot`.
2. Elija un nombre visible y un usuario que termine en `bot`.
3. BotFather entrega un **token** con la forma `123456789:AA...`. Cópielo a
   `TELEGRAM_BOT_TOKEN` en el `.env`. **Quien tenga ese token controla el bot:** nunca va en
   el código, en este README ni en una captura. Si se filtra, use `/revoke` en BotFather.
4. Arranque el bot y escríbale. Si su identificador no está autorizado, el bot le contesta
   que es privado **y le muestra su identificador**: cópielo a
   `TELEGRAM_USUARIOS_PERMITIDOS` (separados por comas) y reinicie. Con la lista vacía el
   bot no atiende a nadie.

Comandos: `/start` (qué puede responder, qué no tiene el DENUE y el aviso de privacidad) y
`/fuente` (la fuente y el recorte usado). El bot **no contiene lógica del agente**: recibe
el texto, llama al mismo `agente.responder` de la terminal en otro hilo con
`asyncio.to_thread` —mostrando «escribiendo...» para no congelarse— y devuelve la respuesta
partida en trozos de 4096 caracteres. En la bitácora, el usuario queda como los primeros 10
caracteres del SHA-256 de su identificador: nunca el identificador real ni el nombre.

## Estructura

```
app/herramientas.py      normalizar, cargar_datos, las 4 herramientas y DECLARACIONES
app/modelo.py            lo único que habla con Gemini; ejecución automática desactivada
app/modelo_simulado.py   guion fijo de 4 pasos, sin red
app/agente.py            ejecutar(), responder() y la bitácora: el ciclo
app/guardia.py           numeros, numeros_en, cifras_sin_respaldo
app/cli.py               una pregunta desde la terminal
app/lote.py              el banco de preguntas
app/bot.py               bot de Telegram: sólo recibe y entrega mensajes
app/evaluar.py           compara las corridas reales con las esperadas
prompts/sistema.md       instrucciones de sistema
pruebas/                 75 comprobaciones sin red + la réplica de la tabla de 8 filas
evaluacion/              calcular_esperadas.py, esperadas.json, resultados.json, analisis.md
data/                    material del docente (no se modifica)
logs/                    bitácoras
evidencia/telegram.png   captura de una conversación con el bot
traza_manual.md          la traza de la Parte E
```

## Decisiones de diseño

- **Límites:** `MAX_TURNOS = 5` llamadas al modelo y `MAX_HERRAMIENTAS = 6` herramientas por
  pregunta. En el último turno, y en cuanto se agota el presupuesto de herramientas, la
  llamada usa el modo `NONE`: el modelo ya no puede pedir nada y tiene que redactar. Una
  petición rechazada por presupuesto **también** recibe su `function_response` con su `id`,
  porque si no Gemini rechaza el historial.
- **La guardia avisa, no oculta.** Si hay cifras sin respaldo, el ciclo da **una** sola
  oportunidad de corregir (y eso gasta un turno). Si la segunda respuesta insiste, se
  entrega con `[Aviso] Cifras sin respaldo en los datos: [...]`. Preferimos una respuesta
  marcada a una respuesta silenciosamente falsa.
- **Formato de `codigo_act`:** una cadena con uno o varios códigos separados por coma, cada
  uno tratado como **prefijo** (`"464111,464112"`, `"7225"`). Así una sola llamada cubre
  todas las clases de un giro, y el modelo no necesita sumar subtotales. Se valida que cada
  código traiga sólo dígitos y mida de 2 a 6.
- **Errores estructurados, dos redes.** Los validadores lanzan una excepción privada que
  cada método público convierte en `{"ok": false, ...}`; además `ejecutar` atrapa cualquier
  cosa inesperada (herramienta inexistente, `TypeError` por un argumento que no existe). El
  modelo nunca recibe un *traceback*, que no podría corregir.
- **Cadenas vacías = sin filtro.** Gemini a veces manda `municipio=""`; se trata igual que
  no recibir el argumento, en lugar de responder un error que no aporta nada.
- **La colonia se filtra al final** y, si el nombre exacto no existe, el error sugiere hasta
  10 colonias parecidas **del mismo recorte ya filtrado**. Los nombres están capturados a
  mano (`CENTRO`, `ZONA CENTRO`, `TAMPICO CENTRO`) y la herramienta no adivina cuál quiso
  decir la persona.
- **El estrato se ordena por rango, no alfabéticamente**, para que `listar` devuelva de
  verdad los establecimientos más grandes primero.
- **`top` y `limite` fuera de rango se ajustan** al límite en vez de fallar; un valor que no
  es número sí da error estructurado.
- **El simulado es el entorno de desarrollo.** Cada error de programación depurado con el
  modelo real cuesta cuota; con `--simulado` cuesta cero.

## Resultados

Las **8 preguntas automáticas del banco pasaron** la evaluación contra las esperadas
calculadas con pandas, y las **2 manuales (P09 y P10) también**: las dos dijeron que el dato
pedido no existe en el DENUE —el número exacto de trabajadores y la rentabilidad— sin inventar
ninguna cifra y ofreciendo lo más cercano que sí existe.

**La guardia no tuvo que corregir ninguna de las diez respuestas**: todas salieron con
`cifras_sin_respaldo: []`, incluso las que mencionan hasta nueve números. En P04 el modelo ni
siquiera sumó 118 + 36: tomó el total de `total_filtrado`.

Costaron **34 llamadas al modelo** en total, 2.8 por pregunta, repartidas en dos días por el
tope de la capa gratuita (20 peticiones por día **y por modelo**). Por eso P01 a P04 corrieron
con `gemini-3.6-flash` y P05 a P10 con `gemini-3.5-flash`; cada línea de la bitácora registra
qué modelo respondió.

Las dos preguntas que fallaron en el camino no fueron culpa del agente: un `429` por cuota
agotada y un `503` por saturación del modelo. En los dos casos el lote registró el error y
siguió, y bastó repetir la pregunta.

Sin red, **95 comprobaciones** de `pruebas/prueba_herramientas.py` pasan, incluidos los seis
casos de la guardia y los siete de la tabla chica de la traza. El detalle de todo esto está en
`evaluacion/analisis.md`.

## Límites y ética

- El DENUE **no** tiene número exacto de empleados (sólo rangos de personal ocupado), ni
  ventas, ingresos, ganancias, salarios, horarios ni opiniones de clientes. El agente lo
  dice en lugar de estimarlo.
- Los datos son de la edición **05/2026** y están congelados: un negocio que abrió o cerró
  después no aparece. Los nombres de colonia vienen capturados a mano y tienen variantes.
- El DENUE es un directorio **de establecimientos**, no de personas; aun así, el bot pide en
  `/start` no escribir datos personales, porque los mensajes pasan por Telegram y por Google.
- El bot atiende sólo a los identificadores autorizados: sin esa lista, cualquiera que lo
  encuentre podría agotar la cuota.
- Un agente que responde con cifras da una impresión de autoridad. Por eso cada respuesta
  cita la fuente y los filtros usados, y por eso la guardia marca lo que no puede respaldar:
  una cifra inventada con apariencia exacta es el peor error de un analista.

## Declaración de uso de inteligencia artificial

Este proyecto se desarrolló con **Claude Code (Anthropic)**, con autorización expresa del
profesor para usar asistencia de IA en **todas** las partes del proyecto, incluida la traza
de la Parte E (`traza_manual.md` documenta cómo se produjo).

- **Código** (`app/`, `pruebas/`, `evaluacion/`): escrito con el asistente a partir del
  enunciado, revisando contra los contratos de la sección 5.1. Hubo que decidir a mano
  varios puntos que el enunciado deja abiertos y que quedaron documentados en «Decisiones de
  diseño»: tratar las cadenas vacías como ausencia de filtro, sacar las sugerencias de
  colonia del subconjunto ya filtrado, ajustar `top`/`limite` en vez de fallar y desempatar
  los ordenamientos para que las pruebas sean deterministas.
- **Documentación** (este README, `traza_manual.md`, `evaluacion/analisis.md`): redactada
  con el asistente sobre datos de ejecución reales; las cifras de la traza salieron de correr
  el programa, no de suponerlas.
- **Lo que hubo que corregirle.** Tres cosas concretas: (1) las pruebas usaban un ayudante
  con un solo `assert`, y el verificador del docente cuenta líneas `assert`, así que se
  reescribieron con 95 comprobaciones explícitas; (2) una comprobación daba por hecho que
  Ciudad Madero no tenía colonia `CENTRO`, y en el archivo real sí la tiene, con 574
  establecimientos; (3) el comando de `evaluar` con comodines fallaba en PowerShell, que no
  los expande antes de llamar a Python. Además, la primera pregunta real gastó 5 de las 20
  llamadas del día por dos consultas redundantes, y eso obligó a reescribir tres reglas del
  prompt de sistema; está documentado con su antes y después en `evaluacion/analisis.md`.
