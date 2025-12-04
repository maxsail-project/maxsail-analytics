[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://maxsail-analytics.streamlit.app/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/maxsail-project/maxsail-analytics)

# maxSail-analytics & maxSail GPX Cutter

**Sailing Data, Better Decisions**

[maxSail-analytics](https://maxsail-analytics.streamlit.app/) · [maxSail GPX Cutter](https://maxsail-gpx-cutter.streamlit.app/) - [maxSail Meta Data](https://maxsail-meta-data.streamlit.app/)

Puedes descargar los GPX de este repo para hacer pruebas o mejor aún: usar los tuyos.  
You can download the GPX files from this repo for testing, or even better: use your own.

---

## Índice / Table of Contents

- [maxSail-analytics \& maxSail GPX Cutter](#maxsail-analytics--maxsail-gpx-cutter)
  - [Índice / Table of Contents](#índice--table-of-contents)
  - [Descripción general / Overview](#descripción-general--overview)
  - [maxSail-analytics](#maxsail-analytics)
    - [Características principales / Main features](#características-principales--main-features)
  - [maxSail GPX Cutter](#maxsail-gpx-cutter)
  - [maxSail Meta Data](#maxsail-meta-data)
  - [Instalación / Installation](#instalación--installation)
  - [Uso básico / Basic usage](#uso-básico--basic-usage)
  - [Formato esperado del archivo CSV / Expected CSV format](#formato-esperado-del-archivo-csv--expected-csv-format)
  - [Sobre el autor / About the author](#sobre-el-autor--about-the-author)
  - [Wiki](#wiki)
  - [Contacto / Contact](#contacto--contact)
  - [Aviso legal / Disclaimer](#aviso-legal--disclaimer)
  - [Licencia / License](#licencia--license)
  - [Contribuciones / Contributions](#contribuciones--contributions)

---
## Descripción general / Overview

**maxSail-analytics** y **maxSail GPX Cutter** son herramientas open source para visualizar, analizar, comparar y limpiar tracks GPS de regatas y entrenamientos de vela ligera y crucero.  
**maxSail-analytics** and **maxSail GPX Cutter** are open-source tools to visualize, analyze, compare, and clean GPS tracks from dinghy and keelboat racing or training sessions.

- **maxSail-analytics:** Análisis, visualización y comparación avanzada de tracks GPX/CSV.  
  **maxSail-analytics:** Advanced analysis, visualization, and comparison of GPX/CSV tracks.

- **maxSail GPX Cutter:** Recorta tramos de tus tracks GPX de forma visual y sencilla, para limpiar y exportar solo lo que te interesa.  
  **maxSail GPX Cutter:** Visually trim segments of your GPX tracks to clean and export only what you need.

- **maxSail Meta Data:** Gestiona fácilmente metadatos de tus tracks (dirección y fuerza del viento, minuto de salida, notas, balizas) mediante archivos `-meta-data.json` asociados a cada GPX. Reproduce, comparte y analiza sesiones con máxima fidelidad.  
  **maxSail Meta Data:** Easily manage track metadata (wind direction and strength, start minute, notes, marks) using `-meta-data.json` files linked to each GPX. Replay, share, and analyze sessions with maximum fidelity.

---

## maxSail-analytics

[maxSail-analytics en Streamlit](https://maxsail-analytics.streamlit.app/)  
[maxSail-analytics on Streamlit](https://maxsail-analytics.streamlit.app/)

**maxSail-analytics** es una herramienta open source para visualizar, analizar y comparar tracks GPS de regatas y entrenamientos de vela.  
**maxSail-analytics** is an open-source tool for visualizing, analyzing, and comparing GPS tracks from sailing races and training sessions.

Permite cargar archivos GPX o CSV, mostrar recorridos en un mapa interactivo, comparar dos tracks, analizar métricas clave (velocidad, distancia, rumbo, tiempo) y detectar maniobras de forma sencilla, visual y colaborativa.  
It allows you to load GPX or CSV files, display tracks on an interactive map, compare two tracks, analyze key metrics (speed, distance, heading, time), and detect maneuvers in a simple, visual, and collaborative way.

### Características principales / Main features

- Visualización de tracks en mapa interactivo.  
  Interactive map track visualization.
- Comparación de dos recorridos lado a lado.  
  Side-by-side track comparison.
- Análisis de velocidad, rumbo, TWA, VMG y distancia recorrida.  
  Analysis of speed, heading, TWA, VMG, and distance.
- Detección automática de maniobras (tacks/gybes).  
  Automatic tack/gybe detection.
- Cálculo y visualización de métricas clave.  
  Key metric calculation and display.
- Compatible con archivos GPX y CSV normalizados.  
  Compatible with GPX and normalized CSV files.
- Interfaz intuitiva y lista para compartir con la flota.  
  Intuitive UI, ready to share with your fleet.
- **Open source y multiplataforma**.  
  **Open source and cross-platform**.

---

## maxSail GPX Cutter

[![Abrir en Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://maxsail-gpx-cutter.streamlit.app/)

**maxSail GPX Cutter** es un utilitario open source que te permite recortar tramos de tus archivos GPX de forma visual e interactiva, pensado para regatistas y navegantes que quieren analizar sólo los tramos relevantes de su track (por ejemplo, eliminando la ida o el regreso a puerto).

> [¡Probar ahora en Streamlit!](https://maxsail-gpx-cutter.streamlit.app/)

---

## maxSail Meta Data

[![Abrir en Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://maxsail-meta-data.streamlit.app/)

**maxSail Meta Data** es un utilitario open source para gestionar y editar los metadatos de tus tracks de navegación (por ejemplo, viento, salida, notas, balizas) mediante archivos `-meta-data.json` vinculados a cada GPX. Pensado para regatistas que buscan reproducibilidad, organización avanzada y análisis colaborativo.

> [¡Probar ahora en Streamlit!](https://maxsail-meta-data.streamlit.app/)

---

## Instalación / Installation

Versión on-line / Online versions:  
- [https://maxsail-analytics.streamlit.app/](https://maxsail-analytics.streamlit.app/)  
- [https://maxsail-gpx-cutter.streamlit.app/](https://maxsail-gpx-cutter.streamlit.app/)

Si quieres usar la aplicación en local sigue estos pasos:  
If you want to use the app locally, follow these steps:

1. Clona el repositorio / Clone the repository:

```sh
   git clone https://github.com/maxsail-project/maxsail-analytics.git
   cd maxsail-analytics
```

1. Instala las dependencias / Install dependencies:

```sh
   pip install streamlit gpxpy pyproj pandas numpy altair pydeck scipy requests haversine matplotlib
```

1. Ejecuta la aplicación / Run the app:

```sh
   streamlit run maxsail-analytics.py
```

Para el cutter, cambia el nombre por el de maxsail-gpx-cutter.py
For the cutter, use maxsail-gpx-cutter.py as the filename.

## Uso básico / Basic usage

- Sube uno o más archivos GPX o CSV desde el panel lateral.\
  Upload one or more GPX or CSV files from the sidebar.
- Selecciona los tracks a comparar.\
  Select tracks to compare.
- Ajusta los parámetros de análisis y explora los resultados en gráficos y tablas.\
  Adjust analysis parameters and explore the results in graphs and tables.
- Exporta o comparte los insights con tu flota.\
  Export or share insights with your fleet.

## Formato esperado del archivo CSV / Expected CSV format

El visor requiere archivos CSV normalizados con al menos estas columnas:\
The viewer expects normalized CSV files with at least the following columns:

| Columna / Column | Descripción / Description                                           | Ejemplo / Example        |
| ---------------- | ------------------------------------------------------------------- | ------------------------ |
| Lat              | Latitud (decimal, WGS84) / Latitude (decimal)                       | −34.945917               |
| Lon              | Longitud (decimal, WGS84) / Longitude (decimal)                     | −55.932721               |
| UTC              | Fecha y hora UTC / UTC datetime (ISO 8601 or YYYY-MM-DD HH\:MM\:SS) | 2024-06-27 14:23:15      |
| COG              | Rumbo sobre el fondo (°) / Course Over Ground (°)                   | 89.0                     |
| SOG              | Velocidad sobre el fondo (knots) / Speed Over Ground (knots)        | 5.33                     |
| Dist             | Distancia entre puntos (m) / Distance between points (m)            | 8.2                      |
| SourceFile (opt) | Nombre del archivo / Source filename                                | 2025-07-ESP30782-P01.GPX |

**Notas / Notes:**

- Columnas adicionales serán ignoradas salvo que coincidan con el formato interno (TWA, VMG, etc.). Extra columns will be ignored unless they match internal format (TWA, VMG, etc.).
- `UTC` debe estar en un formato reconocible por pandas. `UTC` must be in a pandas-recognized datetime format.
- Cada archivo debe tener al menos esas columnas. Each file must contain at least those columns.
- Si no hay `SourceFile`, se usará el nombre del archivo. If `SourceFile` is missing, the filename will be used as track ID.

## Sobre el autor / About the author

¡Hola! Soy Maximiliano Mannise, ingeniero en informática (trabajando desde 1998), fanático de los datos, indicadores y métricas. Navego desde hace más de 20 años: primero por diversión, luego en regatas de crucero y desde 2020 en vela ligera clase Snipe. 
Por deformación profesional, suelo llevar todo al terreno analítico. Aunque existen software muy profesionales para análisis de datos de navegación, buscaba una herramienta **simple, personal, rápida de usar**... y de repente me encontré desarrollando esta aplicación, que ahora comparto con otros regatistas. ¡Estoy seguro de que no soy el único que disfruta mirar los datos después de cada regata! 
Si bien está pensado para analizar información básica a partir de un GPX, se puede extender a análisis más completos con CSV que contengan más variables... algo de eso ya estoy preparando.

Hi! I'm Maximiliano Mannise, a software engineer (working since 1998), data geek, and passionate sailor. I've been sailing for more than 20 years, first for fun, then in cruising regattas, and since 2020, in the Snipe dinghy class.
As a data and analytics fan, I always try to look at sailing from an analytical perspective. While there are very professional tools for navigation log analysis, I wanted something **simple, personal, and fast**...  and I ended up building this app, which I'm now sharing with other sailors. I'm sure I'm not the only one who enjoys looking at post-race data!
This project is meant for basic GPX-based analysis, but it can easily be extended to richer CSV data... I'm already working on that.

**Cualquier colaboración, solicitud de mejora o feedback es muy bienvenido.**\
**¡Nos vemos en el agua!**\
**Any contribution, improvement request, or feedback is welcome.**\
**See you on the water!**

## Wiki

- [Wiki maxSail-analytics by DeepWiki](https://deepwiki.com/maxsail-project/maxsail-analytics)

## Contacto / Contact

- Autor / Author: Maximiliano Mannise
- LinkedIn: [https://www.linkedin.com/in/mmannise](https://www.linkedin.com/in/mmannise)
- Email: [maxsail.project@gmail.com](mailto\:maxsail.project@gmail.com)
- GitHub: maxsail-project

## Aviso legal / Disclaimer

Este visor es un proyecto experimental y de uso abierto.\
Los análisis e información presentados son orientativos y no suponen asesoramiento profesional ni responsabilidad legal.

This viewer is an experimental, open project.\
Analyses and information are for guidance only and do not represent professional advice or legal responsibility.

## Licencia / License

Este proyecto está bajo la licencia MIT.\
This project is under the MIT License.

## Contribuciones / Contributions

¡Las mejoras, sugerencias y forks son bienvenidos!\
Improvements, suggestions and forks are welcome!

Si quieres reportar un bug, proponer una mejora o colaborar, abre un "issue" o un "pull request" en este repositorio.\
If you'd like to report a bug, suggest an enhancement or contribute, please open an issue or pull request in this repository.
