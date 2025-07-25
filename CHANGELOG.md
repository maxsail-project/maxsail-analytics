# CHANGELOG

Todas las novedades, cambios y fixes de **maxSail-analytics** aparecerán aquí.  
All new features, changes, and fixes for **maxSail-analytics** will be listed here.

---
## [1.2.0-beta]

**Versión de trabajo / beta (no estable)**  
Esta versión incorpora funcionalidades en desarrollo que pueden cambiar o mejorarse antes del próximo release estable.

### Agregado
- Gráfico superpuesto de SOG y COG para cada track, permitiendo análisis visual combinado de velocidad y rumbo.
- Detección y visualización avanzada de balizas de recorrido y de salida.
- Mejoras varias en visualización, leyendas y métricas.

### Nota
> Esta versión es de trabajo y puede tener cambios frecuentes. No recomendada para uso en producción o análisis definitivos.
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
