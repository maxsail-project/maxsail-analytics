# maxsail-analytics

**Sailing Data, Better Decisions**  

## Descripción

**maxsail-analytics** es una herramienta open source para visualizar, analizar y comparar tracks GPS de regatas y entrenamientos de vela.  
Permite cargar archivos GPX o CSV, mostrar recorridos en mapa, comparar dos tracks, analizar métricas clave y detectar maniobras, todo de forma sencilla y colaborativa.

**maxsail-analytics** is an open source tool to visualize, analyze, and compare GPS tracks from sailing races and training.  
Upload GPX or CSV files, display tracks on a map, compare two tracks, analyze key performance metrics, and detect maneuvers easily and collaboratively.

## Características principales / Main features

- Visualización de tracks en mapa interactivo.
- Comparación de dos recorridos lado a lado.
- Análisis de velocidad, rumbo, TWA, VMG y distancia recorrida.
- Detección automática de maniobras (tacks/gybes).
- Cálculo y visualización de métricas clave.
- Compatible con archivos GPX y CSV normalizados.
- Interfaz intuitiva y lista para compartir con la flota.
- **Open source y multiplataforma**.

## Instalación / Installation

1. Clona el repositorio / Clone the repository:

```sh
   git clone https://github.com/maxsail-project/maxsail-analytics.git
   cd maxsail-analytics
```

1. Instala las dependencias / Install dependencies:

```sh
   pip install streamlit gpxpy pyproj pandas numpy altair pydeck
```

1. Ejecuta la aplicación / Run the app:

```sh
   streamlit run maxsail-analytics.py
```

## Uso básico / Basic usage

- Sube uno o más archivos GPX o CSV desde el panel lateral.
- Selecciona los tracks a comparar.
- Ajusta los parámetros de análisis y explora los resultados en gráficos y tablas.
- Exporta o comparte los insights con tu flota.

## Formato esperado del archivo CSV

El visor requiere archivos CSV normalizados con al menos estas columnas:

| Columna   | Descripción                                    | Ejemplo         |
|-----------|------------------------------------------------|-----------------|
| Lat       | Latitud (decimal, WGS84)                       | -34.912345      |
| Lon       | Longitud (decimal, WGS84)                      | -56.163421      |
| UTC       | Fecha y hora en UTC (ISO 8601 o YYYY-MM-DD HH:MM:SS) | 2024-06-27 14:23:15 |
| COG       | Rumbo sobre el fondo (°)                       | 89.0            |
| SOG       | Velocidad sobre el fondo (nudos)               | 5.33            |
| Dist      | Distancia entre puntos (metros)                | 8.2             |
| SourceFile (opcional) | Nombre de archivo origen           | regata1.csv     |

**Notas:**
- Si el CSV tiene más columnas, serán ignoradas salvo que coincidan con el formato interno (TWA, VMG, etc.).
- La columna `UTC` debe estar en formato reconocible por pandas (ej: `YYYY-MM-DD HH:MM:SS`).
- Si cargas varios archivos, cada uno debe tener al menos estas columnas.
- Si el archivo no tiene `SourceFile`, se usará el nombre del archivo como identificador de track.

## Contacto / Contact

- Autor / Author: Maximiliano Mannise
- LinkedIn: https://www.linkedin.com/in/mmannise
- Email: maxsail.project@gmail.com
- GitHub: maxsail-project

## Aviso legal / Disclaimer

Este visor es un proyecto experimental y de uso abierto.
Los análisis e información presentados son orientativos y no suponen asesoramiento profesional ni responsabilidad legal.

This viewer is an experimental, open project.
Analyses and information are for guidance only and do not represent professional advice or legal responsibility.

## Licencia / License

Este proyecto está bajo la licencia MIT.
This project is under the MIT License.

## Contribuciones / Contributions

¡Las mejoras, sugerencias y forks son bienvenidos!
Improvements, suggestions and forks are welcome!

Si quieres reportar un bug, proponer una mejora o colaborar, abre un "issue" o un "pull request" en este repositorio.

