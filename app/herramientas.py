"""Parte A - Las herramientas del agente analista del DENUE.

Este modulo es el unico que toca los datos. No habla con el modelo, no usa la red
y no imprime nada: recibe argumentos, consulta un DataFrame de pandas y devuelve
diccionarios listos para viajar como function_response.

Reglas que cumple todo el modulo:

1. Las cifras las calcula pandas, nunca el modelo.
2. Ninguna herramienta lanza excepciones hacia el modelo: un argumento invalido
   produce {"ok": false, "error": "...", "valores_validos": [...] o None}.
3. Todo resultado correcto incluye "ok": true, "fuente" y los "filtros" aplicados
   con el valor ya corregido ("Ciudad Madero" aunque llegara "ciudad madero").
"""

from __future__ import annotations

import unicodedata
from typing import Any

import pandas as pd

# --------------------------------------------------------------------------- #
# Constantes
# --------------------------------------------------------------------------- #

FUENTE = "DENUE 05/2026, INEGI"

MUNICIPIOS: tuple[str, ...] = ("Tampico", "Ciudad Madero")

# De menor a mayor: este orden valida el filtro y ordena el resultado de listar.
ESTRATOS: tuple[str, ...] = (
    "0 a 5 personas",
    "6 a 10 personas",
    "11 a 30 personas",
    "31 a 50 personas",
    "51 a 100 personas",
    "101 a 250 personas",
    "251 y más personas",
)

CAMPOS_RANKING: tuple[str, ...] = ("municipio", "colonia", "sector", "codigo_act", "estrato")
CAMPOS_ESTABLECIMIENTO: tuple[str, ...] = ("id", "nombre", "actividad", "estrato", "colonia", "municipio")

# Columnas que las herramientas necesitan de verdad; el archivo trae mas (direccion,
# coordenadas, fecha_alta) y esas se cargan pero no se exigen.
COLUMNAS_REQUERIDAS: tuple[str, ...] = (
    "id", "nombre", "codigo_act", "actividad", "sector", "estrato", "municipio", "colonia",
)

TOPE_ACTIVIDADES = 15
TOP_MINIMO, TOP_MAXIMO, TOP_OMISION = 1, 20, 5
LIMITE_MINIMO, LIMITE_MAXIMO, LIMITE_OMISION = 1, 20, 10
MIN_LETRAS_PALABRA = 3
MAX_SUGERENCIAS = 10
LARGO_MINIMO_CODIGO, LARGO_MAXIMO_CODIGO = 2, 6


class _ErrorDeFiltro(Exception):
    """Argumento invalido. Nunca sale de este modulo: cada metodo publico la
    atrapa y la convierte en {"ok": false, ...}."""

    def __init__(self, mensaje: str, valores_validos: list[str] | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.valores_validos = valores_validos


# --------------------------------------------------------------------------- #
# Funciones de modulo
# --------------------------------------------------------------------------- #

def normalizar(texto: Any) -> str:
    """Minusculas, sin acentos y con los espacios colapsados.

    >>> normalizar("  Cafeterías,  Neverías ")
    'cafeterias, neverias'
    """
    if texto is None:
        return ""
    if not isinstance(texto, str):
        texto = str(texto)
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_acentos = descompuesto.encode("ascii", "ignore").decode("ascii")
    return " ".join(sin_acentos.lower().split())


def cargar_datos(ruta_denue: str, ruta_sectores: str) -> tuple[pd.DataFrame, dict[str, str]]:
    """Lee los dos CSV y devuelve (DataFrame, {sector: nombre}).

    Lee todo como texto (dtype=str) para que los codigos SCIAN sigan siendo
    cadenas y los prefijos funcionen, y con keep_default_na=False para que las
    celdas vacias queden como "" y no como NaN.

    Agrega colonia_norm y actividad_norm una sola vez, para no normalizar las
    22,900 filas en cada consulta.
    """
    datos = pd.read_csv(ruta_denue, dtype=str, keep_default_na=False)
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in datos.columns]
    if faltantes:
        # Esto es un error del programa (archivo equivocado), no del modelo:
        # aqui si corresponde fallar fuerte y temprano.
        raise ValueError(f"{ruta_denue} no trae las columnas {faltantes}")

    datos = datos.copy()
    datos["colonia_norm"] = datos["colonia"].map(normalizar)
    datos["actividad_norm"] = datos["actividad"].map(normalizar)

    # Del CSV de sectores se usan las dos primeras columnas (codigo, nombre) sin
    # asumir como se llaman.
    tabla = pd.read_csv(ruta_sectores, dtype=str, keep_default_na=False)
    if tabla.shape[1] < 2:
        raise ValueError(f"{ruta_sectores} debe traer al menos dos columnas: codigo y nombre")
    columna_codigo, columna_nombre = tabla.columns[0], tabla.columns[1]
    sectores = {
        str(codigo).strip(): str(nombre).strip()
        for codigo, nombre in zip(tabla[columna_codigo], tabla[columna_nombre])
        if str(codigo).strip()
    }
    return datos, sectores


def _ok(**campos: Any) -> dict[str, Any]:
    """Resultado correcto: siempre con ok y fuente."""
    return {"ok": True, "fuente": FUENTE, **campos}


def _error(mensaje: str, valores_validos: list[str] | None = None) -> dict[str, Any]:
    """Error estructurado: el modelo puede leerlo y corregir."""
    return {"ok": False, "error": mensaje, "valores_validos": valores_validos}


def _texto(valor: Any) -> str | None:
    """Normaliza la ausencia: None y "" (lo que manda el modelo cuando no quiere
    filtrar) son lo mismo que no recibir el argumento."""
    if valor is None:
        return None
    if not isinstance(valor, str):
        valor = str(valor)
    valor = valor.strip()
    return valor or None


def _entero(valor: Any, nombre: str, minimo: int, maximo: int, omision: int) -> int:
    """Convierte a entero y ajusta al limite. Un valor fuera de rango se ajusta;
    un valor que no es numero es un error estructurado."""
    if valor is None or valor == "":
        return omision
    if isinstance(valor, bool):
        raise _ErrorDeFiltro(f"'{nombre}' debe ser un numero entero entre {minimo} y {maximo}")
    if isinstance(valor, int):
        numero = valor
    elif isinstance(valor, float):
        if valor != int(valor):
            raise _ErrorDeFiltro(f"'{nombre}' debe ser un numero entero entre {minimo} y {maximo}")
        numero = int(valor)
    else:
        crudo = str(valor).strip()
        try:
            numero = int(float(crudo))
        except ValueError:
            raise _ErrorDeFiltro(
                f"'{nombre}' debe ser un numero entero entre {minimo} y {maximo}; llego '{valor}'"
            ) from None
    return max(minimo, min(maximo, numero))


def _singular(palabra: str) -> str:
    """Plurales sencillos del espanol: 'hospitales' -> 'hospital',
    'farmacias' -> 'farmacia'."""
    if len(palabra) > 5 and palabra.endswith("es"):
        return palabra[:-2]
    if len(palabra) > 4 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


def _palabras_busqueda(texto: Any) -> list[str]:
    """Palabras utiles de un texto de busqueda: normalizadas, sin puntuacion,
    de MIN_LETRAS_PALABRA letras o mas y en singular."""
    crudo = _texto(texto)
    if crudo is None:
        raise _ErrorDeFiltro(
            "'texto' es obligatorio: escriba el giro que busca, por ejemplo 'farmacia'"
        )
    palabras: list[str] = []
    for bruto in normalizar(crudo).split():
        limpio = "".join(c for c in bruto if c.isalnum())
        if len(limpio) >= MIN_LETRAS_PALABRA:
            palabras.append(_singular(limpio))
    if not palabras:
        raise _ErrorDeFiltro(
            f"'texto' no trae ninguna palabra de {MIN_LETRAS_PALABRA} letras o mas; "
            "escriba el giro que busca, por ejemplo 'farmacia' o 'salon de belleza'"
        )
    return palabras


# --------------------------------------------------------------------------- #
# Las cuatro herramientas
# --------------------------------------------------------------------------- #

class Herramientas:
    """Las cuatro consultas que el modelo puede pedir sobre el DENUE.

    El modelo solo pide; esta clase ejecuta. Ningun metodo evalua codigo del
    modelo, y ninguno lanza excepciones hacia afuera.
    """

    def __init__(self, datos: pd.DataFrame, sectores: dict[str, str]) -> None:
        self.datos = datos
        self.sectores = dict(sectores)

        # Mapas canonicos: normalizado -> valor tal como aparece en el archivo.
        # Se construyen primero con los valores del archivo (por si la captura
        # difiere de la constante) y luego con las constantes como respaldo.
        self._municipios = {normalizar(v): v for v in datos["municipio"].unique() if v}
        for oficial in MUNICIPIOS:
            self._municipios.setdefault(normalizar(oficial), oficial)

        self._estratos = {normalizar(v): v for v in datos["estrato"].unique() if v}
        for oficial in ESTRATOS:
            self._estratos.setdefault(normalizar(oficial), oficial)

        # Orden ordinal del estrato (no alfabetico) para listar.
        self._orden_estrato: dict[str, int] = {}
        for posicion, oficial in enumerate(ESTRATOS):
            valor = self._estratos.get(normalizar(oficial))
            if valor is not None:
                self._orden_estrato[valor] = posicion

        self._estratos_validos = [
            self._estratos[normalizar(o)] for o in ESTRATOS if normalizar(o) in self._estratos
        ]
        self._sectores_validos = sorted(v for v in datos["sector"].unique() if v)

    # ------------------------- validacion de filtros ------------------------ #

    def _municipio(self, valor: Any) -> str:
        crudo = _texto(valor)
        clave = normalizar(crudo)
        if clave not in self._municipios:
            raise _ErrorDeFiltro(
                f"municipio no valido: '{crudo}'. El recorte del DENUE solo trae dos municipios",
                list(MUNICIPIOS),
            )
        return self._municipios[clave]

    def _codigos(self, valor: Any) -> list[str]:
        crudo = _texto(valor)
        codigos = [parte.strip() for parte in str(crudo).split(",")]
        codigos = [c for c in codigos if c]
        if not codigos:
            raise _ErrorDeFiltro(
                "'codigo_act' llego vacio; use buscar_actividades para obtener los codigos"
            )
        for codigo in codigos:
            if not (codigo.isascii() and codigo.isdigit()):
                raise _ErrorDeFiltro(
                    f"codigo de actividad no valido: '{codigo}'. Debe traer solo digitos; "
                    "separe varios con coma ('464111,464112') y use buscar_actividades "
                    "para obtenerlos"
                )
            if not (LARGO_MINIMO_CODIGO <= len(codigo) <= LARGO_MAXIMO_CODIGO):
                raise _ErrorDeFiltro(
                    f"codigo de actividad no valido: '{codigo}'. Debe medir entre "
                    f"{LARGO_MINIMO_CODIGO} y {LARGO_MAXIMO_CODIGO} digitos "
                    "(cada codigo funciona como prefijo SCIAN)"
                )
        return codigos

    def _sector(self, valor: Any) -> str:
        crudo = _texto(valor)
        if crudo not in self._sectores_validos:
            raise _ErrorDeFiltro(
                f"sector no valido: '{crudo}'. El sector son los dos primeros digitos del "
                "codigo SCIAN",
                list(self._sectores_validos),
            )
        return crudo

    def _estrato(self, valor: Any) -> str:
        crudo = _texto(valor)
        clave = normalizar(crudo)
        if clave not in self._estratos:
            raise _ErrorDeFiltro(
                f"estrato no valido: '{crudo}'. El DENUE registra el personal ocupado en rangos "
                "fijos, no como numero exacto",
                list(self._estratos_validos),
            )
        return self._estratos[clave]

    def _filtrar(
        self,
        codigo_act: Any = None,
        municipio: Any = None,
        sector: Any = None,
        estrato: Any = None,
        colonia: Any = None,
    ) -> tuple[pd.DataFrame, dict[str, str]]:
        """Aplica con y logico todos los filtros que se dieron.

        La colonia se aplica al final, sobre lo que quedo de los demas filtros:
        asi las sugerencias de un nombre que no existe salen del mismo recorte
        que pidio el modelo.
        """
        marco = self.datos
        filtros: dict[str, str] = {}

        if _texto(codigo_act) is not None:
            codigos = self._codigos(codigo_act)
            mascara = pd.Series(False, index=marco.index)
            for codigo in codigos:
                mascara = mascara | marco["codigo_act"].str.startswith(codigo)
            marco = marco[mascara]
            filtros["codigo_act"] = ",".join(codigos)

        if _texto(municipio) is not None:
            valor = self._municipio(municipio)
            marco = marco[marco["municipio"] == valor]
            filtros["municipio"] = valor

        if _texto(sector) is not None:
            valor = self._sector(sector)
            marco = marco[marco["sector"] == valor]
            filtros["sector"] = valor

        if _texto(estrato) is not None:
            valor = self._estrato(estrato)
            marco = marco[marco["estrato"] == valor]
            filtros["estrato"] = valor

        if _texto(colonia) is not None:
            objetivo = normalizar(colonia)
            subconjunto = marco[marco["colonia_norm"] == objetivo]
            if subconjunto.empty:
                parecidas = marco.loc[
                    marco["colonia_norm"].str.contains(objetivo, regex=False), "colonia"
                ]
                sugerencias = sorted(set(parecidas))[:MAX_SUGERENCIAS]
                raise _ErrorDeFiltro(
                    f"no hay establecimientos en la colonia '{_texto(colonia)}' con los demas "
                    "filtros dados. Los nombres de colonia estan capturados a mano: use uno de "
                    "los nombres exactos del DENUE",
                    sugerencias or None,
                )
            filtros["colonia"] = str(subconjunto["colonia"].iloc[0])
            marco = subconjunto

        return marco, filtros

    # ----------------------------- herramienta 1 ---------------------------- #

    def buscar_actividades(self, texto: Any = None) -> dict[str, Any]:
        """Clases SCIAN cuyo nombre contiene todas las palabras del texto."""
        try:
            palabras = _palabras_busqueda(texto)
        except _ErrorDeFiltro as falla:
            return _error(falla.mensaje, falla.valores_validos)

        mascara = pd.Series(True, index=self.datos.index)
        for palabra in palabras:
            mascara = mascara & self.datos["actividad_norm"].str.contains(palabra, regex=False)
        coincidencias = self.datos[mascara]

        if coincidencias.empty:
            return _ok(texto=str(texto), palabras=palabras, total_actividades=0, actividades=[])

        conteo = (
            coincidencias.groupby(["codigo_act", "actividad"], sort=False)
            .size()
            .reset_index(name="establecimientos")
            .sort_values(["establecimientos", "codigo_act"], ascending=[False, True])
        )
        actividades = [
            {
                "codigo_act": str(fila.codigo_act),
                "actividad": str(fila.actividad),
                "establecimientos": int(fila.establecimientos),
            }
            for fila in conteo.head(TOPE_ACTIVIDADES).itertuples()
        ]
        return _ok(
            texto=str(texto),
            palabras=palabras,
            total_actividades=int(len(conteo)),
            actividades=actividades,
        )

    # ----------------------------- herramienta 2 ---------------------------- #

    def contar(
        self,
        codigo_act: Any = None,
        municipio: Any = None,
        sector: Any = None,
        estrato: Any = None,
        colonia: Any = None,
    ) -> dict[str, Any]:
        """Cuenta establecimientos que cumplen todos los filtros dados."""
        try:
            marco, filtros = self._filtrar(codigo_act, municipio, sector, estrato, colonia)
        except _ErrorDeFiltro as falla:
            return _error(falla.mensaje, falla.valores_validos)
        return _ok(filtros=filtros, total=int(len(marco)))

    # ----------------------------- herramienta 3 ---------------------------- #

    def ranking(
        self,
        por: Any = None,
        top: Any = None,
        codigo_act: Any = None,
        municipio: Any = None,
        sector: Any = None,
        estrato: Any = None,
        colonia: Any = None,
    ) -> dict[str, Any]:
        """Los valores con mas establecimientos, agrupando por un campo."""
        try:
            campo = normalizar(_texto(por))
            if not campo:
                raise _ErrorDeFiltro("'por' es obligatorio: indique el campo que agrupa", list(CAMPOS_RANKING))
            if campo not in CAMPOS_RANKING:
                raise _ErrorDeFiltro(f"'por' no valido: '{_texto(por)}'", list(CAMPOS_RANKING))
            if _texto(colonia) is not None:
                raise _ErrorDeFiltro(
                    "ranking no acepta el filtro 'colonia': para ver las colonias con mas "
                    "establecimientos use por='colonia', y para una colonia especifica use "
                    "contar o listar"
                )
            cuantos = _entero(top, "top", TOP_MINIMO, TOP_MAXIMO, TOP_OMISION)
            marco, filtros = self._filtrar(codigo_act, municipio, sector, estrato)
        except _ErrorDeFiltro as falla:
            return _error(falla.mensaje, falla.valores_validos)

        serie = marco.loc[marco[campo] != "", campo]
        conteo = (
            serie.value_counts()
            .rename_axis("valor")
            .reset_index(name="total")
            .sort_values(["total", "valor"], ascending=[False, True])
        )

        nombres_actividad: dict[str, str] = {}
        if campo == "codigo_act" and not marco.empty:
            nombres_actividad = (
                marco.drop_duplicates("codigo_act").set_index("codigo_act")["actividad"].to_dict()
            )

        filas: list[dict[str, Any]] = []
        for fila in conteo.head(cuantos).itertuples():
            renglon: dict[str, Any] = {"valor": str(fila.valor), "total": int(fila.total)}
            if campo == "codigo_act":
                renglon["actividad"] = str(nombres_actividad.get(str(fila.valor), ""))
            elif campo == "sector":
                renglon["nombre_sector"] = str(self.sectores.get(str(fila.valor), ""))
            filas.append(renglon)

        return _ok(
            filtros=filtros,
            por=campo,
            top=cuantos,
            total_filtrado=int(len(marco)),
            filas=filas,
        )

    # ----------------------------- herramienta 4 ---------------------------- #

    def listar(
        self,
        limite: Any = None,
        codigo_act: Any = None,
        municipio: Any = None,
        sector: Any = None,
        estrato: Any = None,
        colonia: Any = None,
    ) -> dict[str, Any]:
        """Establecimientos concretos, del estrato mayor al menor."""
        try:
            cuantos = _entero(limite, "limite", LIMITE_MINIMO, LIMITE_MAXIMO, LIMITE_OMISION)
            if all(_texto(f) is None for f in (codigo_act, municipio, sector, estrato, colonia)):
                raise _ErrorDeFiltro(
                    "listar exige al menos un filtro (codigo_act, municipio, sector, estrato o "
                    "colonia): sin filtros seria el directorio completo"
                )
            marco, filtros = self._filtrar(codigo_act, municipio, sector, estrato, colonia)
        except _ErrorDeFiltro as falla:
            return _error(falla.mensaje, falla.valores_validos)

        orden = marco["estrato"].map(self._orden_estrato)
        ordenado = marco.assign(_orden=orden.fillna(-1)).sort_values(
            ["_orden", "nombre"], ascending=[False, True]
        )
        establecimientos = [
            {campo: str(fila[campo]) for campo in CAMPOS_ESTABLECIMIENTO}
            for _, fila in ordenado.head(cuantos).iterrows()
        ]
        return _ok(
            filtros=filtros,
            total=int(len(marco)),
            mostrados=len(establecimientos),
            establecimientos=establecimientos,
        )


# --------------------------------------------------------------------------- #
# Las declaraciones que ve el modelo
# --------------------------------------------------------------------------- #

_DESCRIPCION_CODIGO_ACT = (
    "Uno o varios codigos SCIAN separados por coma ('464111,464112'). Cada codigo funciona "
    "como PREFIJO: '7225' agrupa todas las clases que empiezan con 7225. Obtenlos primero con "
    "buscar_actividades y revisa que el prefijo no incluya clases de otro giro."
)
_DESCRIPCION_MUNICIPIO = "'Tampico' o 'Ciudad Madero'. Omitelo para contar los dos municipios juntos."
_DESCRIPCION_SECTOR = (
    "Sector SCIAN: los dos primeros digitos del codigo de actividad (por ejemplo '46' o '72'). "
    "Igualdad exacta, no prefijo."
)
_DESCRIPCION_ESTRATO = (
    "Rango de personal ocupado, exactamente uno de: " + "; ".join(ESTRATOS) + ". "
    "El DENUE no tiene el numero exacto de empleados."
)
_DESCRIPCION_COLONIA = (
    "Nombre EXACTO de la colonia como lo capturo el INEGI (mayusculas, sin importar acentos). "
    "Los nombres estan capturados a mano y hay variantes ('CENTRO', 'ZONA CENTRO'): si no existe, "
    "el error devuelve en valores_validos las colonias parecidas para que elijas una."
)

DECLARACIONES: list[dict[str, Any]] = [
    {
        "name": "buscar_actividades",
        "description": (
            "Busca clases de actividad SCIAN por palabras de su nombre y devuelve su codigo y "
            "cuantos establecimientos tiene cada una en los dos municipios. Usala SIEMPRE antes "
            "de contar un giro, para saber que codigos existen; si no encuentras nada, prueba con "
            "un sinonimo."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "texto": {
                    "type": "string",
                    "description": (
                        "Palabras del giro que buscas, por ejemplo 'farmacia' o 'salon de belleza'. "
                        "Devuelve las clases cuyo nombre contiene TODAS las palabras de 3 letras o mas."
                    ),
                }
            },
            "required": ["texto"],
        },
    },
    {
        "name": "contar",
        "description": (
            "Cuenta establecimientos que cumplen todos los filtros dados. Sin filtros cuenta todo "
            "el conjunto. Es la unica forma correcta de obtener un total: no sumes tu."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "codigo_act": {"type": "string", "description": _DESCRIPCION_CODIGO_ACT},
                "municipio": {"type": "string", "description": _DESCRIPCION_MUNICIPIO},
                "sector": {"type": "string", "description": _DESCRIPCION_SECTOR},
                "estrato": {"type": "string", "description": _DESCRIPCION_ESTRATO},
                "colonia": {"type": "string", "description": _DESCRIPCION_COLONIA},
            },
        },
    },
    {
        "name": "ranking",
        "description": (
            "Agrupa por un campo y devuelve los valores con mas establecimientos, de mayor a menor. "
            "Usala para preguntas de tipo 'donde se concentran', 'cual es el municipio con mas' o "
            "'como se reparten'. Devuelve tambien total_filtrado, el total que cumple los filtros."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "por": {
                    "type": "string",
                    "description": (
                        "Campo que agrupa: 'municipio', 'colonia', 'sector', 'codigo_act' o 'estrato'."
                    ),
                },
                "top": {
                    "type": "integer",
                    "description": f"Cuantas filas devolver, de {TOP_MINIMO} a {TOP_MAXIMO} (por omision {TOP_OMISION}).",
                },
                "codigo_act": {"type": "string", "description": _DESCRIPCION_CODIGO_ACT},
                "municipio": {"type": "string", "description": _DESCRIPCION_MUNICIPIO},
                "sector": {"type": "string", "description": _DESCRIPCION_SECTOR},
                "estrato": {"type": "string", "description": _DESCRIPCION_ESTRATO},
            },
            "required": ["por"],
        },
    },
    {
        "name": "listar",
        "description": (
            "Devuelve establecimientos concretos (id, nombre, actividad, estrato, colonia, municipio) "
            "ordenados del estrato mayor al menor. Usala para 'cuales son', 'dame ejemplos' o "
            "'que empresas grandes hay'. Exige al menos un filtro."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limite": {
                    "type": "integer",
                    "description": f"Cuantos establecimientos devolver, de {LIMITE_MINIMO} a {LIMITE_MAXIMO} (por omision {LIMITE_OMISION}).",
                },
                "codigo_act": {"type": "string", "description": _DESCRIPCION_CODIGO_ACT},
                "municipio": {"type": "string", "description": _DESCRIPCION_MUNICIPIO},
                "sector": {"type": "string", "description": _DESCRIPCION_SECTOR},
                "estrato": {"type": "string", "description": _DESCRIPCION_ESTRATO},
                "colonia": {"type": "string", "description": _DESCRIPCION_COLONIA},
            },
        },
    },
]
