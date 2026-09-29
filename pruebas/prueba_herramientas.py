"""Parte D - Pruebas sin red.

    python -m pruebas.prueba_herramientas

No toca la red ni el modelo real: usa la tabla chica y el modelo simulado.
Cubre las cuatro herramientas, los errores estructurados de ejecutar, la guardia
(incluidos los seis casos de la traza E.2), el ciclo completo con el simulado y las
tres funciones puras del bot.
"""

from __future__ import annotations

from pathlib import Path

from app import agente
from app.agente import Bitacora, ejecutar, responder
from app.bot import leer_permitidos, partir_mensaje, usuario_anonimo
from app.guardia import aviso, cifras_sin_respaldo, mensaje_correccion, numeros, numeros_en
from app.herramientas import Herramientas, cargar_datos, normalizar
from app.modelo_simulado import TEXTO_PASO_4, TEXTO_SIN_PRESUPUESTO, ModeloSimulado

# La tabla de 8 filas de la traza E.3. Se usa data/mini_denue.csv (del docente) si
# existe; si no, la réplica que vive en pruebas/.
RUTA_MINI = "data/mini_denue.csv" if Path("data/mini_denue.csv").exists() else "pruebas/mini_denue_replica.csv"
RUTA_SECTORES_MINI = (
    "data/sectores_scian.csv"
    if Path("data/sectores_scian.csv").exists()
    else "pruebas/sectores_scian_replica.csv"
)
RUTA_DENUE = "data/denue_tampico_madero.csv"
RUTA_SECTORES = "data/sectores_scian.csv"
TOTAL_DENUE = 22900  # documentado en el proyecto; ajústelo si su edición trae otra cantidad

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


def comprobar(descripcion: str, condicion: bool, detalle: object = "") -> None:
    global _cuenta
    _cuenta += 1
    assert condicion, f"FALLÓ la comprobación {_cuenta}: {descripcion} {detalle}"
    print(f"  {_cuenta:2d}. OK  {descripcion}")


def main() -> int:
    datos, sectores = cargar_datos(RUTA_MINI, RUTA_SECTORES_MINI)
    h = Herramientas(datos, sectores)

    print("\nnormalizar")
    comprobar("quita acentos y colapsa espacios", normalizar("  Cafeterías,  Neverías ") == "cafeterias, neverias")
    comprobar("la ñ se vuelve n", normalizar("DOÑA LUPE") == "dona lupe")
    comprobar("None es cadena vacía", normalizar(None) == "")

    print("\ncargar_datos")
    comprobar("agrega colonia_norm y actividad_norm", {"colonia_norm", "actividad_norm"} <= set(datos.columns))
    comprobar("los códigos siguen siendo texto", datos["codigo_act"].map(type).eq(str).all())
    comprobar("el diccionario de sectores tiene nombres", all(isinstance(v, str) and v for v in sectores.values()))

    print("\nlas cuatro herramientas sobre la tabla chica (traza E.3)")
    h1 = h.contar(municipio="tampico")
    comprobar("H1 contar(municipio='tampico') = 5", h1["total"] == 5, h1)
    comprobar("H1 corrige el municipio en filtros", h1["filtros"]["municipio"] == "Tampico", h1)
    comprobar("H1 trae la fuente", h1["fuente"] == "DENUE 05/2026, INEGI", h1)
    h2 = h.contar(codigo_act="4641")
    comprobar("H2 el prefijo 4641 alcanza 4 filas, no sólo farmacias", h2["total"] == 4, h2)
    h3 = h.contar(codigo_act="464111,464112", municipio="Ciudad Madero")
    comprobar("H3 dos códigos y un municipio = 2", h3["total"] == 2, h3)
    h4 = h.ranking(por="colonia", top=2, municipio="Tampico")
    comprobar("H4 ranking por colonia en Tampico", [(f["valor"], f["total"]) for f in h4["filas"]] == [("CENTRO", 3), ("LAS AMERICAS", 2)], h4)
    comprobar("H4 trae por y total_filtrado", h4["por"] == "colonia" and h4["total_filtrado"] == 5, h4)
    h5 = h.listar(limite=2, codigo_act="7225")
    comprobar("H5 listar ordena del estrato mayor al menor", [e["nombre"] for e in h5["establecimientos"]] == ["TAQUERIA DONA LUPE", "CAFE DEL PUERTO"], h5)
    comprobar("H5 trae total y mostrados", h5["total"] == 3 and h5["mostrados"] == 2, h5)
    h6 = h.buscar_actividades("farmacias")
    comprobar("H6 el plural se vuelve singular", h6["palabras"] == ["farmacia"], h6)
    comprobar("H6 dos clases, de más a menos establecimientos", [(a["codigo_act"], a["establecimientos"]) for a in h6["actividades"]] == [("464111", 2), ("464112", 1)], h6)
    h7 = h.contar(colonia="centro", municipio="Ciudad Madero")
    comprobar("H7 colonia inexistente en ese municipio da ok:false", h7["ok"] is False, h7)

    print("\nerrores estructurados y casos de borde de las herramientas")
    e = h.contar(municipio="Monterrey")
    comprobar("municipio inválido lista los dos válidos", e["ok"] is False and e["valores_validos"] == ["Tampico", "Ciudad Madero"], e)
    e = h.contar(codigo_act="46A")
    comprobar("código con letras da error claro", e["ok"] is False and "46A" in e["error"], e)
    e = h.contar(codigo_act="4")
    comprobar("código de un dígito da error", e["ok"] is False, e)
    e = h.contar(estrato="quince empleados")
    comprobar("estrato inválido lista los estratos del archivo", e["ok"] is False and len(e["valores_validos"]) >= 1, e)
    e = h.contar(sector="99")
    comprobar("sector inexistente lista los sectores", e["ok"] is False and "46" in e["valores_validos"], e)
    e = h.listar()
    comprobar("listar sin filtros da error", e["ok"] is False and "al menos un filtro" in e["error"], e)
    e = h.ranking(por="colonia", colonia="CENTRO")
    comprobar("ranking rechaza el filtro colonia", e["ok"] is False, e)
    e = h.ranking(por="calle")
    comprobar("por inválido lista los campos válidos", e["ok"] is False and "municipio" in e["valores_validos"], e)
    e = h.buscar_actividades("de la")
    comprobar("texto sin palabras útiles da error", e["ok"] is False, e)
    vacio = h.buscar_actividades("zapatería industrial de cohetes")
    comprobar("sin coincidencias devuelve lista vacía, no error", vacio["ok"] is True and vacio["actividades"] == [], vacio)
    comprobar("municipio='' es lo mismo que no filtrar", h.contar(municipio="")["total"] == 8)
    comprobar("top fuera de rango se ajusta al límite", h.ranking(por="municipio", top=99)["top"] == 20)
    comprobar("limite fuera de rango se ajusta al límite", h.listar(limite=0, municipio="Tampico")["mostrados"] == 1)
    comprobar("top como texto se convierte", h.ranking(por="municipio", top="2")["top"] == 2)
    e = h.listar(limite="muchos", municipio="Tampico")
    comprobar("limite no numérico da error estructurado", e["ok"] is False, e)
    r = h.ranking(por="codigo_act", top=1)
    comprobar("ranking por codigo_act agrega la actividad", "actividad" in r["filas"][0], r)
    r = h.ranking(por="sector", top=1)
    comprobar("ranking por sector agrega nombre_sector", r["filas"][0]["nombre_sector"] != "", r)
    s = h.contar(colonia="las americas")
    comprobar("la colonia se compara sin acentos ni mayúsculas", s["total"] == 2 and s["filtros"]["colonia"] == "LAS AMERICAS", s)
    sug = h.contar(colonia="america")
    comprobar("colonia parcial sugiere nombres exactos", sug["ok"] is False and sug["valores_validos"] == ["LAS AMERICAS"], sug)

    print("\nejecutar: ninguna excepción llega al modelo")
    e = ejecutar(h, "consultar_sql", {})
    comprobar("herramienta inexistente", e["ok"] is False and "inexistente" in e["error"], e)
    e = ejecutar(h, "contar", {"ciudad": "Tampico"})
    comprobar("argumento que no existe (TypeError)", e["ok"] is False and "ciudad" in e["error"], e)
    e = ejecutar(h, "contar", {"municipio": "Monterrey"})
    comprobar("el error de la herramienta pasa tal cual", e["ok"] is False and e["valores_validos"] == ["Tampico", "Ciudad Madero"], e)
    e = ejecutar(h, "listar", {})
    comprobar("listar sin filtros a través de ejecutar", e["ok"] is False, e)
    e = ejecutar(h, "contar", "municipio=Tampico")
    comprobar("argumentos que no son objeto", e["ok"] is False, e)
    comprobar("una llamada válida pasa por ejecutar", ejecutar(h, "contar", {"municipio": "Tampico"})["total"] == 5)

    print("\nla guardia de cifras")
    comprobar("comas de miles", numeros("Tampico tiene 1,570 taquerías.") == {1570})
    comprobar("marcas de lista no cuentan", numeros("1. Tampico: 570\n2) Madero: 296") == {570, 296})
    comprobar("decimales y ceros al inicio", numeros("05 de 5.5 y 7.0") == {5, 5.5, 7})
    comprobar("texto sin cifras", numeros("no hay datos de ventas") == set())
    comprobar("numeros_en recorre la estructura", numeros_en(RESULTADOS_E2) >= {866, 570, 296, 722514, 5, 2026})
    comprobar("True, False y None no aportan cifras", numeros_en({"a": True, "b": False, "c": None}) == set())
    comprobar("los números de Python cuentan como su texto", numeros_en({"total": 154, "x": 5.5}) == {154, 5.5})

    print("\nlos seis casos de la traza E.2")
    g = lambda respuesta: cifras_sin_respaldo(respuesta, PREGUNTA_E2, RESULTADOS_E2)
    comprobar("G1 cifras correctas: sin faltantes", g("Tampico tiene 570 taquerías y Ciudad Madero 296.") == [])
    comprobar("G2 la diferencia calculada se detecta", g("Tampico tiene 570 y Madero 296: una diferencia de 274.") == [274])
    comprobar("G3 el porcentaje calculado se detecta", g("En total hay 866; Tampico concentra el 65.8 %.") == [65.8])
    comprobar("G4 la lista numerada pasa limpia", g("1. Tampico: 570\n2. Ciudad Madero: 296\nClase SCIAN 722514, DENUE 05/2026.") == [])
    comprobar("G5 la cifra inflada se detecta", g("Tampico tiene 1,570 taquerías.") == [1570])
    comprobar("G6 los municipios intercambiados PASAN la guardia", g("Ciudad Madero tiene 570 taquerías y Tampico 296.") == [])
    comprobar("el mensaje de corrección nombra las cifras", "[274]" in mensaje_correccion([274]))
    comprobar("el aviso nombra las cifras", "[1570]" in aviso([1570]))

    print("\nel ciclo completo con el modelo simulado")
    bitacora = Bitacora(modelo="simulado", ruta=None)
    fin = responder("¿Cuántas farmacias hay en Tampico?", h, "sistema de prueba", ModeloSimulado(), bitacora)
    comprobar("termina en el turno 4 (la corrección gasta uno)", fin["turnos"] == 4, fin)
    comprobar("usó 2 herramientas", fin["herramientas"] == 2, fin)
    comprobar("entrega el texto del paso 4", fin["respuesta"].startswith(TEXTO_PASO_4.split("\n")[0]), fin)
    comprobar(
        "la secuencia de eventos es la del algoritmo",
        bitacora.nombres_de_eventos() == ["inicio", "modelo", "herramienta", "modelo", "herramienta", "modelo", "guardia", "modelo", "guardia", "fin"],
        bitacora.nombres_de_eventos(),
    )
    guardias = [e for e in bitacora.eventos if e["evento"] == "guardia"]
    comprobar("la guardia detuvo la respuesta del turno 3", guardias[0]["cifras_sin_respaldo"] == [160], guardias[0])
    comprobar("la segunda guardia ya viene corregida", guardias[1]["corregida"] is True, guardias[1])
    herramientas_pedidas = [e["nombre"] for e in bitacora.eventos if e["evento"] == "herramienta"]
    comprobar("pidió buscar_actividades y luego contar", herramientas_pedidas == ["buscar_actividades", "contar"], herramientas_pedidas)

    print("\nel presupuesto de herramientas")
    original = agente.MAX_HERRAMIENTAS
    try:
        agente.MAX_HERRAMIENTAS = 1
        bitacora_corta = Bitacora(modelo="simulado", ruta=None)
        corto = responder("¿Cuántas farmacias hay en Tampico?", h, "sistema", ModeloSimulado(), bitacora_corta)
    finally:
        agente.MAX_HERRAMIENTAS = original
    comprobar("con MAX_HERRAMIENTAS=1 termina en el turno 2", corto["turnos"] == 2, corto)
    comprobar("sólo ejecutó una herramienta", corto["herramientas"] == 1, corto)
    comprobar("cierra con el texto de presupuesto agotado", corto["respuesta"].startswith(TEXTO_SIN_PRESUPUESTO), corto)

    print("\nlas tres funciones puras del bot")
    comprobar("leer_permitidos separa por comas", leer_permitidos("123, 456 ,789") == {123, 456, 789})
    comprobar("leer_permitidos vacío no atiende a nadie", leer_permitidos("") == set() and leer_permitidos(None) == set())
    comprobar("leer_permitidos ignora basura", leer_permitidos("abc, 12") == {12})
    largo = ("x" * 100 + "\n") * 60
    trozos = partir_mensaje(largo, 1000)
    comprobar("partir_mensaje respeta el tope", all(len(t) <= 1000 for t in trozos), [len(t) for t in trozos])
    comprobar("partir_mensaje corta en salto de línea", all(not t.startswith("x" * 101) for t in trozos))
    comprobar("partir_mensaje no parte lo corto", partir_mensaje("corto") == ["corto"])
    comprobar("usuario_anonimo son 10 caracteres estables", usuario_anonimo(123456789) == usuario_anonimo("123456789") and len(usuario_anonimo(1)) == 10)

    if Path(RUTA_DENUE).exists() and Path(RUTA_SECTORES).exists():
        print("\nel archivo completo del DENUE")
        datos_completos, sectores_completos = cargar_datos(RUTA_DENUE, RUTA_SECTORES)
        completo = Herramientas(datos_completos, sectores_completos)
        total = completo.contar()["total"]
        comprobar(f"contar sin filtros da el total del archivo ({total})", total == TOTAL_DENUE, total)
        suma = completo.contar(municipio="Tampico")["total"] + completo.contar(municipio="Ciudad Madero")["total"]
        comprobar("los dos municipios suman el total", suma == total, suma)
        farmacias = completo.buscar_actividades("farmacia")
        comprobar("buscar_actividades encuentra la clase 464111", any(a["codigo_act"] == "464111" for a in farmacias["actividades"]), farmacias)
        rank = completo.ranking(por="municipio")
        comprobar("ranking por municipio devuelve dos filas que suman el total", sum(f["total"] for f in rank["filas"]) == total, rank)
        grandes = completo.listar(limite=5, municipio="Tampico")
        comprobar("listar devuelve establecimientos del municipio pedido", all(x["municipio"] == "Tampico" for x in grandes["establecimientos"]), grandes)
    else:
        print(f"\n[aviso] {RUTA_DENUE} no está: las comprobaciones del archivo completo se omiten.")

    print(f"\n{_cuenta} comprobaciones OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
