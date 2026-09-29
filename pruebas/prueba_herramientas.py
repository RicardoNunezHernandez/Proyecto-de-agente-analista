"""Parte D - Pruebas sin red.

    python -m pruebas.prueba_herramientas

No toca la red ni el modelo real: usa la tabla de 8 filas, el archivo completo del
DENUE y el modelo simulado. Cubre las cuatro herramientas, los errores estructurados
de ejecutar, la guardia (incluidos los seis casos de la traza E.2), el ciclo completo
con el simulado y las tres funciones puras del bot.
"""

from __future__ import annotations

from pathlib import Path

from app import agente
from app.agente import Bitacora, ejecutar, responder
from app.bot import leer_permitidos, partir_mensaje, usuario_anonimo
from app.guardia import aviso, cifras_sin_respaldo, mensaje_correccion, numeros, numeros_en
from app.herramientas import Herramientas, cargar_datos, normalizar
from app.modelo_simulado import TEXTO_PASO_4, TEXTO_SIN_PRESUPUESTO, ModeloSimulado

RUTA_MINI = "data/mini_denue.csv"
RUTA_DENUE = "data/denue_tampico_madero.csv"
RUTA_SECTORES = "data/sectores_scian.csv"

# Resultados conocidos del archivo completo (DENUE 05/2026, verificados con pandas
# aparte, en evaluacion/calcular_esperadas.py).
TOTAL_DENUE = 22900
TOTAL_TAMPICO = 15716
TOTAL_MADERO = 7184
FARMACIAS_TAMPICO = 154
TAQUERIAS_TAMPICO = 570
TAQUERIAS_MADERO = 296
CAFETERIAS_TAMPICO = 184
GRANDES_MADERO = 11

PREGUNTA_E2 = (
    "¿Dónde hay más taquerías, en Tampico o en Ciudad Madero? "
    "Dame la cifra de cada municipio."
)
RESULTADOS_E2 = [
    {
        "ok": True,
        "fuente": "DENUE 05/2026, INEGI",
        "actividades": [
            {
                "codigo_act": "722514",
                "actividad": "Restaurantes con servicio de preparación de tacos y tortas",
                "establecimientos": 866,
            }
        ],
    },
    {
        "ok": True,
        "fuente": "DENUE 05/2026, INEGI",
        "por": "municipio",
        "filtros": {"codigo_act": "722514"},
        "total_filtrado": 866,
        "filas": [
            {"valor": "Tampico", "total": 570},
            {"valor": "Ciudad Madero", "total": 296},
        ],
    },
]

_cuenta = 0


def ok(descripcion: str) -> None:
    """Cuenta e informa una comprobación que pasó."""
    global _cuenta
    _cuenta += 1
    print(f"  {_cuenta:2d}. OK  {descripcion}")


def main() -> int:
    datos, sectores = cargar_datos(RUTA_MINI, RUTA_SECTORES)
    h = Herramientas(datos, sectores)

    print("\nnormalizar")
    assert normalizar("  Cafeterías,  Neverías ") == "cafeterias, neverias", normalizar("  Cafeterías,  Neverías ")
    ok("quita acentos y colapsa espacios")
    assert normalizar("DOÑA LUPE") == "dona lupe", normalizar("DOÑA LUPE")
    ok("la ñ se vuelve n")
    assert normalizar(None) == "" and normalizar(464111) == "464111"
    ok("None da cadena vacía y un número da su texto")

    print("\ncargar_datos")
    assert {"colonia_norm", "actividad_norm"} <= set(datos.columns), list(datos.columns)
    ok("agrega colonia_norm y actividad_norm")
    assert datos["codigo_act"].map(type).eq(str).all()
    ok("los códigos siguen siendo texto, no números")
    assert sectores["46"] == "Comercio al por menor" and sectores["31-33"] == "Industrias manufactureras", sectores.get("46")
    ok("el diccionario de sectores incluye los compuestos (31-33)")

    print("\nlas cuatro herramientas sobre la tabla chica (traza E.3)")
    h1 = h.contar(municipio="tampico")
    assert h1["total"] == 5, h1
    ok("H1 contar(municipio='tampico') = 5")
    assert h1["filtros"]["municipio"] == "Tampico", h1
    ok("H1 corrige el municipio en filtros")
    assert h1["fuente"] == "DENUE 05/2026, INEGI", h1
    ok("H1 trae la fuente")
    h2 = h.contar(codigo_act="4641")
    assert h2["total"] == 4, h2
    ok("H2 el prefijo 4641 alcanza 4 filas, no sólo las farmacias")
    h3 = h.contar(codigo_act="464111,464112", municipio="Ciudad Madero")
    assert h3["total"] == 2, h3
    ok("H3 dos códigos y un municipio = 2")
    h4 = h.ranking(por="colonia", top=2, municipio="Tampico")
    assert [(f["valor"], f["total"]) for f in h4["filas"]] == [("CENTRO", 3), ("LAS AMERICAS", 2)], h4
    ok("H4 ranking por colonia en Tampico")
    assert h4["por"] == "colonia" and h4["total_filtrado"] == 5, h4
    ok("H4 trae por y total_filtrado")
    h5 = h.listar(limite=2, codigo_act="7225")
    assert [normalizar(e["nombre"]) for e in h5["establecimientos"]] == ["taqueria dona lupe", "cafe del puerto"], h5
    ok("H5 listar ordena del estrato mayor al menor")
    assert h5["total"] == 3 and h5["mostrados"] == 2, h5
    ok("H5 trae total y mostrados")
    h6 = h.buscar_actividades("farmacias")
    assert h6["palabras"] == ["farmacia"], h6
    ok("H6 el plural se vuelve singular")
    assert [(a["codigo_act"], a["establecimientos"]) for a in h6["actividades"]] == [("464111", 2), ("464112", 1)], h6
    ok("H6 dos clases, de más a menos establecimientos")
    h7 = h.contar(colonia="centro", municipio="Ciudad Madero")
    assert h7["ok"] is False, h7
    ok("H7 colonia inexistente en ese municipio da ok:false")

    print("\nerrores estructurados y casos de borde")
    e = h.contar(municipio="Monterrey")
    assert e["ok"] is False and e["valores_validos"] == ["Tampico", "Ciudad Madero"], e
    ok("municipio inválido lista los dos válidos")
    e = h.contar(codigo_act="46A")
    assert e["ok"] is False and "46A" in e["error"], e
    ok("código con letras da error claro")
    e = h.contar(codigo_act="4")
    assert e["ok"] is False, e
    ok("código de un solo dígito da error")
    e = h.contar(estrato="quince empleados")
    assert e["ok"] is False and "0 a 5 personas" in e["valores_validos"], e
    ok("estrato inválido lista los estratos válidos")
    e = h.contar(sector="99")
    assert e["ok"] is False and "46" in e["valores_validos"], e
    ok("sector inexistente lista los sectores del archivo")
    e = h.listar()
    assert e["ok"] is False and "al menos un filtro" in e["error"], e
    ok("listar sin filtros da error")
    e = h.ranking(por="colonia", colonia="CENTRO")
    assert e["ok"] is False, e
    ok("ranking rechaza el filtro colonia")
    e = h.ranking(por="calle")
    assert e["ok"] is False and "municipio" in e["valores_validos"], e
    ok("por inválido lista los campos válidos")
    e = h.ranking()
    assert e["ok"] is False, e
    ok("ranking sin por da error")
    e = h.buscar_actividades("de la")
    assert e["ok"] is False, e
    ok("texto sin palabras útiles da error")
    e = h.buscar_actividades()
    assert e["ok"] is False, e
    ok("buscar_actividades sin texto da error")
    vacio = h.buscar_actividades("zapatería industrial de cohetes")
    assert vacio["ok"] is True and vacio["actividades"] == [], vacio
    ok("sin coincidencias devuelve lista vacía, no error")
    assert h.contar(municipio="")["total"] == 8, h.contar(municipio="")
    ok("municipio='' es lo mismo que no filtrar")
    assert h.ranking(por="municipio", top=99)["top"] == 20
    ok("top fuera de rango se ajusta al límite")
    assert h.listar(limite=0, municipio="Tampico")["mostrados"] == 1
    ok("limite fuera de rango se ajusta al límite")
    assert h.ranking(por="municipio", top="2")["top"] == 2
    ok("top como texto se convierte")
    e = h.listar(limite="muchos", municipio="Tampico")
    assert e["ok"] is False, e
    ok("limite no numérico da error estructurado")
    r = h.ranking(por="codigo_act", top=1)
    assert "actividad" in r["filas"][0], r
    ok("ranking por codigo_act agrega la actividad")
    r = h.ranking(por="sector", top=1)
    assert r["filas"][0]["nombre_sector"] != "", r
    ok("ranking por sector agrega nombre_sector")
    s = h.contar(colonia="las americas")
    assert s["total"] == 2 and s["filtros"]["colonia"] == "LAS AMERICAS", s
    ok("la colonia se compara sin acentos ni mayúsculas")
    sug = h.contar(colonia="america")
    assert sug["ok"] is False and sug["valores_validos"] == ["LAS AMERICAS"], sug
    ok("colonia parcial sugiere el nombre exacto")

    print("\nejecutar: ninguna excepción llega al modelo")
    e = ejecutar(h, "consultar_sql", {})
    assert e["ok"] is False and "inexistente" in e["error"], e
    ok("herramienta inexistente")
    e = ejecutar(h, "contar", {"ciudad": "Tampico"})
    assert e["ok"] is False and "ciudad" in e["error"], e
    ok("argumento que no existe (TypeError)")
    e = ejecutar(h, "contar", {"municipio": "Monterrey"})
    assert e["ok"] is False and e["valores_validos"] == ["Tampico", "Ciudad Madero"], e
    ok("el error de la herramienta pasa tal cual")
    e = ejecutar(h, "listar", {})
    assert e["ok"] is False, e
    ok("listar sin filtros a través de ejecutar")
    e = ejecutar(h, "contar", "municipio=Tampico")
    assert e["ok"] is False, e
    ok("argumentos que no son un objeto")
    assert ejecutar(h, "contar", {"municipio": "Tampico"})["total"] == 5
    ok("una llamada válida pasa por ejecutar")
    assert ejecutar(h, "contar", None)["total"] == 8
    ok("args None se trata como sin filtros")

    print("\nla guardia de cifras")
    assert numeros("Tampico tiene 1,570 taquerías.") == {1570}
    ok("comas de miles")
    assert numeros("1. Tampico: 570\n2) Madero: 296") == {570, 296}
    ok("las marcas de lista no cuentan")
    assert numeros("05 de 5.5 y 7.0") == {5, 5.5, 7}
    ok("decimales, ceros al inicio y decimal cero")
    assert numeros("no hay datos de ventas") == set()
    ok("texto sin cifras")
    assert numeros_en(RESULTADOS_E2) >= {866, 570, 296, 722514, 5, 2026}
    ok("numeros_en recorre diccionarios y listas")
    assert numeros_en({"a": True, "b": False, "c": None}) == set()
    ok("True, False y None no aportan cifras")
    assert numeros_en({"total": 154, "x": 5.5}) == {154, 5.5}
    ok("los números de Python cuentan como su texto")

    print("\nlos seis casos de la traza E.2")
    assert cifras_sin_respaldo("Tampico tiene 570 taquerías y Ciudad Madero 296.", PREGUNTA_E2, RESULTADOS_E2) == []
    ok("G1 cifras correctas: nada sin respaldo")
    assert cifras_sin_respaldo("Tampico tiene 570 y Madero 296: una diferencia de 274.", PREGUNTA_E2, RESULTADOS_E2) == [274]
    ok("G2 la diferencia calculada se detecta")
    assert cifras_sin_respaldo("En total hay 866; Tampico concentra el 65.8 %.", PREGUNTA_E2, RESULTADOS_E2) == [65.8]
    ok("G3 el porcentaje calculado se detecta")
    assert cifras_sin_respaldo("1. Tampico: 570\n2. Ciudad Madero: 296\nClase SCIAN 722514, DENUE 05/2026.", PREGUNTA_E2, RESULTADOS_E2) == []
    ok("G4 la lista numerada pasa limpia")
    assert cifras_sin_respaldo("Tampico tiene 1,570 taquerías.", PREGUNTA_E2, RESULTADOS_E2) == [1570]
    ok("G5 la cifra inflada se detecta")
    assert cifras_sin_respaldo("Ciudad Madero tiene 570 taquerías y Tampico 296.", PREGUNTA_E2, RESULTADOS_E2) == []
    ok("G6 los municipios intercambiados PASAN la guardia")
    assert "[274]" in mensaje_correccion([274]) and "Corrige" in mensaje_correccion([274])
    ok("el mensaje de corrección nombra las cifras")
    assert "[1570]" in aviso([1570])
    ok("el aviso nombra las cifras")

    print("\nel ciclo completo con el modelo simulado")
    bitacora = Bitacora(modelo="simulado", ruta=None)
    fin = responder("¿Cuántas farmacias hay en Tampico?", h, "sistema de prueba", ModeloSimulado(), bitacora)
    assert fin["turnos"] == 4, fin
    ok("termina en el turno 4 (la corrección gasta uno)")
    assert fin["herramientas"] == 2, fin
    ok("usó 2 herramientas")
    assert fin["respuesta"].startswith(TEXTO_PASO_4.split("\n")[0]), fin
    ok("entrega el texto del paso 4")
    assert bitacora.nombres_de_eventos() == ["inicio", "modelo", "herramienta", "modelo", "herramienta", "modelo", "guardia", "modelo", "guardia", "fin"], bitacora.nombres_de_eventos()
    ok("la secuencia de eventos es la del algoritmo")
    guardias = [x for x in bitacora.eventos if x["evento"] == "guardia"]
    assert guardias[0]["cifras_sin_respaldo"] == [160], guardias[0]
    ok("la guardia detuvo la respuesta del turno 3")
    assert guardias[1]["corregida"] is True, guardias[1]
    ok("la segunda guardia ya viene corregida")
    assert [x["nombre"] for x in bitacora.eventos if x["evento"] == "herramienta"] == ["buscar_actividades", "contar"]
    ok("pidió buscar_actividades y luego contar")

    print("\nel presupuesto de herramientas")
    original = agente.MAX_HERRAMIENTAS
    try:
        agente.MAX_HERRAMIENTAS = 1
        bitacora_corta = Bitacora(modelo="simulado", ruta=None)
        corto = responder("¿Cuántas farmacias hay en Tampico?", h, "sistema", ModeloSimulado(), bitacora_corta)
    finally:
        agente.MAX_HERRAMIENTAS = original
    assert corto["turnos"] == 2, corto
    ok("con MAX_HERRAMIENTAS=1 termina en el turno 2")
    assert corto["herramientas"] == 1, corto
    ok("sólo ejecutó una herramienta")
    assert corto["respuesta"].startswith(TEXTO_SIN_PRESUPUESTO), corto
    ok("cierra con el texto de presupuesto agotado")
    assert bitacora_corta.nombres_de_eventos() == ["inicio", "modelo", "herramienta", "modelo", "guardia", "fin"], bitacora_corta.nombres_de_eventos()
    ok("la secuencia del cierre forzado es la esperada")

    print("\nlas tres funciones puras del bot")
    assert leer_permitidos("123, 456 ,789") == {123, 456, 789}
    ok("leer_permitidos separa por comas")
    assert leer_permitidos("") == set() and leer_permitidos(None) == set()
    ok("leer_permitidos vacío no atiende a nadie")
    assert leer_permitidos("abc, 12") == {12}
    ok("leer_permitidos ignora la basura")
    largo = ("x" * 100 + "\n") * 60
    trozos = partir_mensaje(largo, 1000)
    assert all(len(t) <= 1000 for t in trozos), [len(t) for t in trozos]
    ok("partir_mensaje respeta el tope")
    assert all(not t.startswith("x" * 101) for t in trozos)
    ok("partir_mensaje corta en un salto de línea")
    assert partir_mensaje("corto") == ["corto"] and partir_mensaje("") == []
    ok("partir_mensaje no parte lo corto")
    assert usuario_anonimo(123456789) == usuario_anonimo("123456789") and len(usuario_anonimo(1)) == 10
    ok("usuario_anonimo son 10 caracteres estables")
    assert usuario_anonimo(123456789) != "123456789"
    ok("usuario_anonimo no deja el identificador real")

    print("\nel archivo completo del DENUE")
    completos, sectores_completos = cargar_datos(RUTA_DENUE, RUTA_SECTORES)
    c = Herramientas(completos, sectores_completos)
    assert c.contar()["total"] == TOTAL_DENUE, c.contar()
    ok(f"contar sin filtros da el total del archivo ({TOTAL_DENUE})")
    assert c.contar(municipio="Ciudad Madero")["total"] == TOTAL_MADERO, c.contar(municipio="Ciudad Madero")
    ok(f"contar por municipio da Ciudad Madero = {TOTAL_MADERO} (P01)")
    assert c.contar(municipio="Tampico")["total"] + TOTAL_MADERO == TOTAL_DENUE
    ok(f"los dos municipios suman el total ({TOTAL_TAMPICO} + {TOTAL_MADERO})")
    assert c.contar(codigo_act="464111,464112", municipio="Tampico")["total"] == FARMACIAS_TAMPICO
    ok(f"farmacias en Tampico = {FARMACIAS_TAMPICO} (P04)")
    assert c.contar(codigo_act="722515", municipio="Tampico")["total"] == CAFETERIAS_TAMPICO
    ok(f"cafeterías en Tampico = {CAFETERIAS_TAMPICO} (P02)")
    assert c.contar(estrato="251 y más personas", municipio="Ciudad Madero")["total"] == GRANDES_MADERO
    ok(f"establecimientos de 251 y más en Madero = {GRANDES_MADERO} (P08)")
    taquerias = c.ranking(por="municipio", codigo_act="722514")
    assert [(f["valor"], f["total"]) for f in taquerias["filas"]] == [("Tampico", TAQUERIAS_TAMPICO), ("Ciudad Madero", TAQUERIAS_MADERO)], taquerias
    ok(f"ranking de taquerías por municipio = {TAQUERIAS_TAMPICO} y {TAQUERIAS_MADERO} (P05)")
    assert taquerias["total_filtrado"] == TAQUERIAS_TAMPICO + TAQUERIAS_MADERO, taquerias
    ok("total_filtrado coincide con la suma de las filas")
    belleza = c.ranking(por="colonia", top=1, municipio="Ciudad Madero", codigo_act="812110")
    assert belleza["filas"][0] == {"valor": "UNIDAD NACIONAL", "total": 52}, belleza
    ok("la colonia con más salones de belleza en Madero es UNIDAD NACIONAL con 52 (P07)")
    sector = c.ranking(por="sector", top=1, municipio="Tampico")
    assert sector["filas"][0]["valor"] == "46" and sector["filas"][0]["nombre_sector"] == "Comercio al por menor", sector
    ok("el sector con más establecimientos en Tampico es 46, Comercio al por menor (P06)")
    farmacias = c.buscar_actividades("farmacias")
    assert [a["codigo_act"] for a in farmacias["actividades"]] == ["464111", "464112"], farmacias
    ok("buscar_actividades encuentra las dos clases de farmacia, la mayor primero")
    grandes = c.listar(limite=3, estrato="251 y más personas", municipio="Ciudad Madero")
    assert grandes["total"] == GRANDES_MADERO and grandes["mostrados"] == 3, grandes
    ok("listar respeta el límite y reporta el total real (P08)")
    assert all(x["municipio"] == "Ciudad Madero" for x in grandes["establecimientos"]), grandes
    ok("listar devuelve sólo establecimientos del municipio pedido")
    exacta = c.contar(colonia="centro", municipio="Ciudad Madero")
    assert exacta["ok"] is True and exacta["filtros"]["colonia"] == "CENTRO", exacta
    ok("una colonia que sí existe exactamente se cuenta (CENTRO en Madero)")
    parcial = c.contar(colonia="unidad nacio", municipio="Ciudad Madero")
    assert parcial["ok"] is False and "UNIDAD NACIONAL" in parcial["valores_validos"], parcial
    ok("un nombre incompleto no se adivina: sugiere los nombres exactos del DENUE")

    print(f"\n{_cuenta} comprobaciones OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
