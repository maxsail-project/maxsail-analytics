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

