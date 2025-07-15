# CHANGELOG

Todas las novedades, cambios y fixes de **maxSail-analytics** aparecerán aquí.  
All new features, changes, and fixes for **maxSail-analytics** will be listed here.

---

## [v1.0.0] - PMV / MVP - 2024-07-15

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
