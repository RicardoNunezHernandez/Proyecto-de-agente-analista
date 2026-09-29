# Diccionario de datos · `denue_tampico_madero.csv`

- **Fuente:** INEGI, Directorio Estadístico Nacional de Unidades Económicas (DENUE), edición 05/2026, entidad 28 (Tamaulipas).
- **Recorte:** municipios de Tampico (15,716 establecimientos) y Ciudad Madero (7,184). Total: 22,900 filas.
- **Formato:** CSV en UTF-8 con encabezado. Léalo con `dtype=str, keep_default_na=False`.

| Columna | Descripción | Ejemplo |
|---|---|---|
| `id` | Identificador del establecimiento en el DENUE | `6277025` |
| `nombre` | Nombre del establecimiento, en mayúsculas | `TECNOLOGICO MADERO` |
| `codigo_act` | Clase de actividad SCIAN, 6 dígitos | `611312` |
| `actividad` | Nombre de la clase de actividad | `Escuelas de educación superior del sector público` |
| `sector` | Sector SCIAN (2 dígitos, o `31-33`, `48-49`) | `61` |
| `estrato` | Personal ocupado, por rangos | `251 y más personas` |
| `municipio` | `Tampico` o `Ciudad Madero` | `Ciudad Madero` |
| `tipo_asentamiento` | Colonia, fraccionamiento, unidad habitacional… | `COLONIA` |
| `colonia` | Nombre del asentamiento, en mayúsculas y tal como se capturó | `RICARDO FLORES MAGON` |
| `codigo_postal` | Código postal | `89440` |
| `calle` | Tipo y nombre de la vialidad | `AVENIDA 1 DE MAYO` |
| `numero_exterior` | Número exterior (puede venir vacío) | `1610` |
| `tipo_unidad` | `Fijo` o `Semifijo` | `Fijo` |
| `latitud`, `longitud` | Coordenadas geográficas | `22.25`, `-97.86` |
| `fecha_alta` | Año y mes de alta en el directorio | `2010-07` |

## Estratos de personal ocupado

`0 a 5 personas` · `6 a 10 personas` · `11 a 30 personas` · `31 a 50 personas` · `51 a 100 personas` · `101 a 250 personas` · `251 y más personas`

El DENUE **no** registra el número exacto de empleados, ventas, ingresos ni salarios.

## Código SCIAN

| Dígitos | Nivel | Ejemplo |
|---|---|---|
| 2 | Sector | `72` Servicios de alojamiento temporal y de preparación de alimentos y bebidas |
| 3 | Subsector | `722` Servicios de preparación de alimentos y bebidas |
| 4 | Rama | `7225` |
| 5 | Subrama | `72251` |
| 6 | Clase | `722515` Cafeterías, fuentes de sodas, neverías, refresquerías y similares |

Los nombres de los sectores están en `sectores_scian.csv`.

## Advertencias

- Los nombres de colonia se capturaron a mano. Un mismo lugar puede aparecer escrito de varias formas.
- Un prefijo de código puede incluir clases que no pertenecen al giro buscado.
