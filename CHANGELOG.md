# CHANGELOG

Todas las novedades, cambios y fixes de **maxSail-analytics** aparecerán aquí.  
All new features, changes, and fixes for **maxSail-analytics** will be listed here.

---

## [v1.2.1] - 2025-12-18

### Español 🇪🇸

#### Nuevas funcionalidades

- **SOGS (velocidad suavizada):** Añadida al procesamiento en `utils.py` mediante media móvil centrada e integrada en los gráficos de velocidad para mejorar la estabilidad visual en tramos afectados por ruido GPS.
- **Sincronización temporal por UTC entre tracks:**  
  Al comparar dos tracks, ambos se sincronizan ahora por **hora GPS (UTC)**, recortando automáticamente los puntos fuera del tramo común.  
  El visor trabaja sobre `df1_sync` / `df2_sync`, garantizando comparaciones coherentes incluso cuando los tracks comienzan en momentos distintos.
- **Soporte para TWDShift (rolada / cambio de recorrido):**  
  Añadido el campo **TWDShift** en metadatos para reflejar cambios de dirección del viento respecto al TWD inicial.

#### Correcciones

- Corregido el cálculo de `time_diff` y la gestión de `prev_point`, eliminando picos de velocidad falsos.
- Eliminación de puntos duplicados exactos (lat/lon) y aplicación de un umbral mínimo de distancia para evitar distorsiones en la velocidad.
- Correcciones en la carga y edición de metadatos (TWD, **TWDShift**, TWS, TWSG, minuto de salida y notas).
- Corregido el comportamiento del visor al comparar tracks con distintos tiempos de inicio, evitando desalineaciones temporales.
- Añadida dependencia faltante `haversine` para evitar errores de importación.

#### Refactor y mejoras

- Refactorizada la tabla resumen del tramo en una única vista compacta y comparativa.
- Añadidas métricas de eficiencia basadas en distancia efectiva (calculada con VMG).
- Incorporados deltas positivos/negativos entre barcos para facilitar la comparación directa.
- Añadidos COG dominantes como referencia táctica del tramo.
- Mejorada la visualización del mapa mostrando el track completo atenuado y resaltando el tramo filtrado.
- Refactor del selector de tramo temporal:
  - Simplificado el selector de tramo temporal en la barra lateral.
  - Ajustada la lógica de minutos + segundos sin modificar el comportamiento funcional.
- Visualización de metadatos:
  - Unificada la visualización compacta de metadatos clave (TWD, TWDShift, TWS, TWSG, NOTAS).
  - Mejora de los mensajes de aviso relacionados con archivos de metadatos no coincidentes.
- Eliminado gráfico redundante **COG vs COG**.
- Reordenados los gráficos para mejorar el flujo visual y la claridad del visor.
- Ajustes menores de texto y visualización en la Rosa de COG.
- Simplificación del mensaje de advertencia cuando el archivo de metadatos no coincide con los tracks cargados.

#### Documentación

- Actualizado README con nueva sección **maxSail Meta Data** y mejoras en instrucciones de instalación.
- Actualización del CHANGELOG para reflejar esta versión y los cambios introducidos.

---

### English 🇬🇧

#### New Features

- **SOGS (Smoothed Speed):** Added to `utils.py` using a centered moving average and integrated into the speed charts to improve visual stability in GPS-noisy segments.
- **UTC-based track synchronization:**  
  When comparing two tracks, both are now synchronized by **GPS time (UTC)**, automatically trimming data outside the common time window.  
  The viewer operates on `df1_sync` / `df2_sync`, ensuring consistent comparisons even when tracks start at different times.
- **TWDShift support (wind shift / course change):**  
  Added **TWDShift** metadata field to represent wind direction changes relative to the initial TWD.

#### Fixes

- Fixed `time_diff` calculation and `prev_point` handling, removing false speed spikes.
- Removed exact duplicate GPX points and applied a minimum distance threshold to avoid unrealistic speed values.
- Fixed metadata loading and editing (TWD, **TWDShift**, TWS, TWSG, start minute and notes).
- Fixed track comparison behavior when tracks start at different times, preventing temporal misalignment.
- Added missing dependency `haversine` to prevent import errors.

#### Refactor & Improvements

- Refactored the leg summary into a single compact and comparative table.
- Added efficiency metrics based on effective distance (computed using VMG).
- Included positive/negative deltas between boats for direct performance comparison.
- Added dominant COG values as tactical references for the leg.
- Improved map visualization by displaying the full track faded and highlighting the selected segment.
- Time segment selector refactor:
  - Simplified the time segment selector in the sidebar.
  - Adjusted minute + second handling without changing functional behavior.
- Metadata visualization:
  - Unified compact visualization of key metadata (TWD, TWDShift, TWS, TWSG, NOTES).
  - Improved warning messages related to mismatched metadata files.
- Removed redundant **COG vs COG** chart.
- Reorganized chart layout to improve visual flow and clarity.
- Minor visualization and labeling improvements in the COG Rose.
- Simplified warning message for metadata file name mismatch.

#### Documentation

- Updated README with the new **maxSail Meta Data** section and enhanced installation notes.
- Updated CHANGELOG with details for this release.

---

## [v1.2.0] - 2025-12-04

### Español 🇪🇸

- **Nuevo:** Análisis de separación entre tracks tanto sobre el peldaño (perpendicular al viento) como sobre el eje del viento (progresión hacia boya/barlovento/sotavento) al inicio y al final del tramo seleccionado.
- **Nuevo:** Tabla comparativa de distancia, tipo de tramo (ceñida, popa/través), barco delante y métrica (lateral o longitudinal).
- **Nuevo:** Permite importar y cargar automáticamente ficheros de metadatos (`-meta-data.json`) junto con el archivo GPX. Los metadatos incluyen TWD, TWS, minuto de salida, notas y balizas personalizadas.
- **Nuevo:** Soporte completo para edición y exportación de metadatos en formato JSON reutilizable entre sesiones.
- Mejora de la sección comparativa por track: incluye fechas/hora de inicio y fin.
- Mejora de visualización en mapa: reducción de tamaño de marcadores de inicio/fin y líneas perpendiculares (mayor claridad al hacer zoom).
- Optimización en cálculo de métricas (COG, TWA, dispersión circular, etc.).
- Mejoras en leyendas, explicaciones y captions bilingües.
- Actualización de dependencias y refactorización de funciones en `utils.py`.
- Se mantiene compatibilidad total con GPX, CSV y tracks de frecuencia variable.
- Análisis de separación entre tracks (peldaño y eje del viento) en inicio y fin de tramo.
- Mejoras en leyendas, visualización y tablas comparativas.
- Optimización de utilidades y flujo de usuario en editor y visor de metadatos.

### English 🇬🇧

- **New:** Analysis of track separation both over the “ladder rung” (perpendicular to wind) and along the wind axis (progression towards the mark/barlo/downwind) at the start and end of the selected leg.
- **New:** Comparative table for distance, leg type (upwind, downwind/reach), leading boat, and metric (lateral/longitudinal).
- **New:** Now supports importing and auto-loading metadata files (`-meta-data.json`) together with GPX files. Metadata includes TWD, TWS, start minute, notes, and custom marks/buoys.
- **New:** Full support for editing and exporting reusable metadata in JSON format across sessions.
- Improved track comparison section: now includes start/end date and time.
- Map visualization improvement: reduced marker size for start/end points and ladder lines for better clarity when zoomed in.
- Optimization of metric calculations (COG, TWA, circular stddev, etc.).
- Enhanced bilingual captions and explanations throughout.
- Updated dependencies and refactored core sailing functions in `utils.py`.
- Full compatibility with GPX, CSV, and tracks of variable frequency maintained.
- Track separation analysis (ladder and wind axis) at start and end of selected segment.
- Improved legends, visualization, and comparative tables.
- Optimized utilities and user workflow in metadata editor and viewer.

---

## [v1.1.0] - 2025-07-24

### Español 🇪🇸

- **Mejora de métricas y visualización comparativa:**
  - Añadida tabla comparativa clara con indicador de barco delante y distancia (m).
  - Nueva métrica de “distancia recorrida de más vs otro track” para analizar eficiencia de ruta.
  - Distancia recorrida mostrada tanto en millas náuticas como en metros.
  - Leyenda dinámica de colores y nombres GPX sobre el mapa, con escala gráfica.
  - Textos y nombres de filas simplificados para mayor claridad.
- **Migración de mapas a MapTiler:**
  - Reemplazado Mapbox por MapTiler como proveedor de mapas (requiere API Key).
  - Selector de fondo de mapa en sidebar (Base, Mapa, Satélite).
  - Visualización más fluida y preparada para futuras capas avanzadas.
- **maxSail GPX Cutter:**
  - Visualización comparada del track original (gris) y recorte (rojo) en un solo mapa con leyenda.
  - Mejor manejo de extensiones GPX y funciones de exportación.
  - Opción para seleccionar fondo de mapa (Base, Mapa, Satélite).
  - Ajuste de filtro de tramos por duración, ahora permite decimales para mayor precisión.
- **Nueva utilidad:**  
  - `setup_venv.bat` para facilitar la creación rápida del entorno virtual.
- **Refactor y mejoras técnicas:**
  - Limpieza de código y comentarios para coherencia entre apps.
  - Mejoras en el cálculo de distancias entre tracks y visualización de track normalizada.
  - Optimización y ampliación de funciones náuticas en `utils.py`.
  - Actualización de dependencias en `requirements.txt`.
  - Actualización de `.gitignore` para cubrir más entornos.
- **Documentación:**
  - README ampliado, badges y estructura mejorada.
  - Sección wiki y enlaces útiles añadidos.
- **Corrección de bugs y detalles menores.**

---

### English 🇬🇧

- **Improved metrics and comparative visualization:**
  - New comparison table indicating leading boat and distance (m).
  - “Extra distance sailed vs. other track” metric for route efficiency analysis.
  - Distance now shown in both nautical miles and meters.
  - Dynamic color and GPX name legend on map, with graphic scale.
  - Simplified text and row names for clarity.
- **MapTiler migration:**
  - Switched from Mapbox to MapTiler for maps (API Key required).
  - Sidebar map style selector (Base, Map, Satellite).
  - Smoother map display, ready for future advanced layers.
- **maxSail GPX Cutter:**
  - Compared view of original (grey) and cut (red) track on a single map with legend.
  - Improved handling of GPX extensions and export functions.
  - Base map style selection option (Base, Map, Satellite).
  - Segment filtering now allows decimal durations for higher precision.
- **New utility:**  
  - `setup_venv.bat` for fast virtual environment setup.
- **Refactor and technical improvements:**
  - Code clean-up and comments for consistency across apps.
  - Improved distance calculation between tracks and normalized track visualization.
  - Expanded and optimized sailing functions in `utils.py`.
  - Updated dependencies in `requirements.txt`.
  - `.gitignore` expanded for more environments.
- **Documentation:**
  - Expanded README, badges and improved structure.
  - Wiki section and helpful links added.
- **Bug fixes and minor improvements.**

---


## [v1.0.0] - versión incial - PMV / MVP - 2024-07-15

### Español 🇪🇸

- **Lanzamiento PMV (Producto Mínimo Viable) de maxSail-analytics.**
- Visualización y comparación de tracks GPX y CSV normalizados en mapa interactivo (PyDeck y Altair).
- Soporte multi-track (dos tracks en paralelo, colores azul/naranja y selección en sidebar).
- Filtros de tramo seleccionable por rango de minutos y segundos.
- Ingreso manual de TWD (True Wind Direction) y recálculo dinámico de TWA/VMG.
- Métricas principales por track: SOG promedio, máximo, TWA medio, VMG promedio, distancia, duración.
- Tabla comparativa de tracks, fechas/hora de inicio y fin, diferencia de distancias.
- Gráficos de evolución para SOG, COG, VMG y TWA (incluye resumen y dispersión de COG por desviación circular).
- Histogramas y gráficos de dispersión SOG vs TWA y VMG vs TWA.
- Detección automática de maniobras (tacks/gybes) configurable por umbral de cambio de COG, ventana y tiempo mínimo.
- Tabla detallada de velocidad media antes y después de cada maniobra, con tiempo de recuperación de SOG previa.
- Análisis de tramos entre maniobras: SOG, COG, desviación circular de COG, TWA promedio y clasificación (ceñida, través, popa).
- Ranking y análisis de mejores/peores tramos de ceñida y popa (ventana deslizante, VMG).
- Visualización de datos de contacto, disclaimers, formato esperado del CSV y ayuda bilingüe ES/EN.
- Refactorización de cálculos náuticos en **utils.py** (distancias, rumbos, velocidades, conversión GPX a CSV, etc).
- Código abierto bajo licencia MIT, preparado para contribuciones de la comunidad.

---

### English 🇬🇧

- **PMV (Minimum Viable Product) release of maxSail-analytics.**
- Interactive map visualization and comparison of GPX and normalized CSV tracks (PyDeck and Altair).
- Multi-track support (two tracks side-by-side, blue/orange colors, sidebar selection).
- Flexible segment filtering by minute/second range.
- Manual TWD (True Wind Direction) input with dynamic TWA/VMG recalculation.
- Main metrics per track: average/max SOG, mean TWA, average VMG, distance, duration.
- Comparative table: track start/end date-time, distance differences.
- Time-series charts for SOG, COG, VMG, TWA (including COG dispersion via circular stddev).
- Histograms and scatter plots: SOG vs TWA and VMG vs TWA.
- Automatic maneuver (tack/gybe) detection: user-configurable thresholds, window, min time.
- Detailed maneuver table: speed before/after, recovery time for pre-maneuver SOG.
- Analysis of segments between maneuvers: mean SOG, COG, circular COG stddev, mean TWA and classification (upwind, reach, downwind).
- Ranking and analysis of best/worst upwind/downwind segments (sliding window, VMG).
- Bilingual ES/EN interface, clear CSV format docs, contact info and disclaimer.
- Core sailing calculations refactored into **utils.py** (distance, heading, speed, GPX→CSV...).
- Open source under MIT License, ready for community contributions.

---

*Este archivo irá creciendo con cada nueva versión.*  
*This file will be updated with every new version.*
