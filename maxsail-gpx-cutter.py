import streamlit as st
import gpxpy
import pandas as pd
import pydeck as pdk
from datetime import datetime, timedelta
import os
import io

# Optional FIT support (requires: pip install fitparse)
try:
    from fitparse import FitFile
except Exception:
    FitFile = None

st.set_page_config(page_title="maxSail GPX Cutter", layout="wide")
st.title("⛵ maxSail GPX Cutter")

# -------- MAPTILER SETUP --------
MAPTILER_KEY = "1TpHMPPswY7nGJWlOXjY"
MAPTILER_STYLES = {
    "Base": f"https://api.maptiler.com/maps/backdrop/style.json?key={MAPTILER_KEY}",
    "Mapa": f"https://api.maptiler.com/maps/landscape/style.json?key={MAPTILER_KEY}",
    "Satélite": f"https://api.maptiler.com/maps/satellite/style.json?key={MAPTILER_KEY}",
}
fondo = st.sidebar.selectbox("Fondo de mapa", list(MAPTILER_STYLES.keys()), index=0)
map_style = MAPTILER_STYLES[fondo]

# --- Sidebar: subir archivo (GPX / VKX / FIT) ---
uploaded_file = st.sidebar.file_uploader(
    "📂 Selecciona un archivo (GPX / VKX / FIT)",
    type=["gpx", "vkx", "fit"],
    accept_multiple_files=False,
)

# --- Funciones ---
def gpx_to_df(gpx):
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                pt_data = {
                    "lat": point.latitude,
                    "lon": point.longitude,
                    "time": point.time
                }
                # Capturamos posibles extensiones
                if point.extensions:
                    for ext in point.extensions:
                        tag = ext.tag.lower()
                        pt_data[tag] = ext.text
                points.append(pt_data)
    return pd.DataFrame(points)

def df_to_gpx(df):
    gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    for _, row in df.iterrows():
        pt = gpxpy.gpx.GPXTrackPoint(
            latitude=row.lat,
            longitude=row.lon,
            time=row.time
        )
        gpx_segment.points.append(pt)
    return gpx.to_xml()

def get_gpx_metadata(gpx, df):
    start_time = df['time'].min()
    end_time = df['time'].max()
    duration = end_time - start_time
    device = gpx.creator if gpx.creator else "Desconocido"
    num_tracks = len(gpx.tracks)
    num_segments = sum(len(track.segments) for track in gpx.tracks)
    extra_fields = list(set(df.columns) - {"lat", "lon", "time"})
    return {
        "Fecha/hora inicio": start_time,
        "Fecha/hora fin": end_time,
        "Duración": duration,
        "Dispositivo": device,
        "Tracks": num_tracks,
        "Segmentos": num_segments,
        "Campos extra": extra_fields
    }

def filtrar_por_minuto(df, min_ini, min_fin):
    t0 = df['time'].iloc[0]
    df = df.copy()
    df['minutes'] = (df['time'] - t0).dt.total_seconds() / 60
    return df[(df['minutes'] >= min_ini) & (df['minutes'] <= min_fin)].copy()

def filtrar_por_timestamp(df, ts_ini, ts_fin):
    df = df.copy()
    if ts_ini:
        try:
            ts_ini = pd.to_datetime(ts_ini)
            df = df[df['time'] >= ts_ini]
        except Exception as e:
            st.warning(f"Timestamp de inicio inválido: {ts_ini}")
    if ts_fin:
        try:
            ts_fin = pd.to_datetime(ts_fin)
            df = df[df['time'] <= ts_fin]
        except Exception as e:
            st.warning(f"Timestamp de fin inválido: {ts_fin}")
    return df


# --- Importers: VKX / FIT -> GPX (in-memory) ---
def vkx_bytes_to_gpx_xml(vkx_bytes: bytes, *, name: str = "Vakaros VKX") -> str:
    """Convert Vakaros VKX bytes to GPX XML (minimal: lat/lon/time/ele).

    Extracts row 0x02 per VKX v1.4 public specification.
    """
    import datetime as dt
    import struct
    import xml.etree.ElementTree as ET

    # Fixed payload sizes by row key (bytes), per VKX spec.
    row_sizes = {
        0xFF: 7, 0xFE: 2, 0x02: 44, 0x03: 20, 0x04: 13, 0x05: 17, 0x06: 18,
        0x08: 13, 0x0A: 16, 0x0B: 16, 0x0C: 12, 0x0F: 16, 0x10: 12,
        # internal rows (skip correctly)
        0x01: 32, 0x07: 12, 0x0E: 16, 0x20: 13, 0x21: 52,
    }

    bio = io.BytesIO(vkx_bytes)
    pts = []

    # Row 0x02: <Q ii 7f  => ts_ms, lat_e7, lon_e7, sog_mps, cog_rad, alt_m, qw,qx,qy,qz
    fmt_02 = "<Qii" + "f" * 7

    while True:
        key_b = bio.read(1)
        if not key_b:
            break
        key = key_b[0]
        size = row_sizes.get(key)
        if size is None:
            # Unknown key: stop to avoid misalignment
            break
        payload = bio.read(size)
        if len(payload) != size:
            break

        if key == 0x02:
            ts_ms, lat_e7, lon_e7, sog_mps, cog_rad, alt_m, qw, qx, qy, qz = struct.unpack(fmt_02, payload)
            t = dt.datetime.fromtimestamp(ts_ms / 1000.0, tz=dt.timezone.utc)
            pts.append((t, lat_e7 * 1e-7, lon_e7 * 1e-7, float(alt_m)))

    pts.sort(key=lambda x: x[0])

    ns = "http://www.topografix.com/GPX/1/1"
    ET.register_namespace("", ns)

    gpx = ET.Element(f"{{{ns}}}gpx", attrib={"version": "1.1", "creator": "maxSail GPX Cutter"})
    meta = ET.SubElement(gpx, f"{{{ns}}}metadata")
    meta_time = pts[0][0] if pts else dt.datetime.now(dt.timezone.utc)
    ET.SubElement(meta, f"{{{ns}}}time").text = meta_time.isoformat().replace("+00:00", "Z")

    trk = ET.SubElement(gpx, f"{{{ns}}}trk")
    ET.SubElement(trk, f"{{{ns}}}name").text = name
    seg = ET.SubElement(trk, f"{{{ns}}}trkseg")

    for t, lat, lon, ele in pts:
        trkpt = ET.SubElement(seg, f"{{{ns}}}trkpt", attrib={"lat": f"{lat:.7f}", "lon": f"{lon:.7f}"})
        ET.SubElement(trkpt, f"{{{ns}}}ele").text = f"{ele:.2f}"
        ET.SubElement(trkpt, f"{{{ns}}}time").text = t.isoformat().replace("+00:00", "Z")

    return ET.tostring(gpx, encoding="utf-8", xml_declaration=True).decode("utf-8")


def fit_bytes_to_gpx_xml(fit_bytes: bytes, *, name: str = "FIT Track") -> str:
    """Convert FIT bytes to GPX XML (minimal: lat/lon/time/ele)."""
    if FitFile is None:
        raise RuntimeError("Dependencia 'fitparse' no disponible. Instala: pip install fitparse")

    import gpxpy.gpx

    fit = FitFile(io.BytesIO(fit_bytes))
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    track.name = name
    gpx.tracks.append(track)
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    for record in fit.get_messages('record'):
        fields = {d.name: d.value for d in record}
        if 'position_lat' in fields and 'position_long' in fields:
            lat = fields['position_lat'] * (180 / 2**31)
            lon = fields['position_long'] * (180 / 2**31)
            elevation = fields.get('altitude')
            time = fields.get('timestamp')
            point = gpxpy.gpx.GPXTrackPoint(latitude=lat, longitude=lon, elevation=elevation, time=time)
            segment.points.append(point)

    return gpx.to_xml()

# --- Main ---
if uploaded_file:
    ext = uploaded_file.name.lower().split(".")[-1]

    if ext == "gpx":
        gpx = gpxpy.parse(uploaded_file)
    elif ext == "vkx":
        vkx_bytes = uploaded_file.read()
        gpx_xml = vkx_bytes_to_gpx_xml(vkx_bytes, name=os.path.splitext(uploaded_file.name)[0])
        gpx = gpxpy.parse(io.StringIO(gpx_xml))
    elif ext == "fit":
        fit_bytes = uploaded_file.read()
        try:
            gpx_xml = fit_bytes_to_gpx_xml(fit_bytes, name=os.path.splitext(uploaded_file.name)[0])
        except Exception as e:
            st.error(f"No se pudo convertir FIT a GPX: {e}")
            st.stop()
        gpx = gpxpy.parse(io.StringIO(gpx_xml))
    else:
        st.error("Formato no soportado. Usa GPX, VKX o FIT.")
        st.stop()

    df = gpx_to_df(gpx)
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    total_duration = (df['time'].iloc[-1] - df['time'].iloc[0]).total_seconds() / 60

    # --- Sidebar: filtros de inicio/fin (en minutos y segundos) ---
    st.sidebar.header("🎚️ Selección de tramo")
    min_duration = int(total_duration)

    # Calcular los valores exactos del último punto
    last_time = df['time'].iloc[-1]
    start_time = df['time'].iloc[0]
    delta_seconds = (last_time - start_time).total_seconds()
    last_minute = int(delta_seconds // 60)
    last_second = int(delta_seconds % 60)
    min_ini = st.sidebar.number_input("Minuto inicial", min_value=0, max_value=min_duration, value=0, step=1)
    sec_ini = st.sidebar.number_input("Segundo inicial", min_value=0, max_value=59, value=0, step=5)
    min_fin = st.sidebar.number_input("Minuto final", min_value=0, max_value=min_duration, value=last_minute, step=1)
    sec_fin = st.sidebar.number_input("Segundo final", min_value=0, max_value=59, value=last_second, step=5)
    start_min = min_ini + sec_ini / 60
    end_min = min_fin + sec_fin / 60
    start_min, end_min = st.sidebar.slider(
        "Tramo seleccionado (minutos decimales)",
        0.0, float(total_duration),
        (start_min, end_min),
        step=0.5
    )
    st.sidebar.markdown("#### (Opcional) Recorte por fecha/hora exacta")
    timestamp_inicio = st.sidebar.text_input(
        "Timestamp de inicio YYYY-MM-DD HH:MM:SS+00:00 (UTC)", 
        value=""
    )
    timestamp_fin = st.sidebar.text_input(
        "Timestamp de fin YYYY-MM-DD HH:MM:SS+00:00 (UTC)", 
        value=""
    )

    # --- Panel principal: información del track ---
    st.header("🧭 Información del track original")
    meta = get_gpx_metadata(gpx, df)
    meta["Archivo original"] = uploaded_file.name
    meta_df = pd.DataFrame([meta]).T
    meta_df.columns = ['Valor']
    st.table(meta_df)

    # --- Recorte según tramo seleccionado o timestamp ---
    if timestamp_inicio.strip() or timestamp_fin.strip():
        df_recorte = filtrar_por_timestamp(df, timestamp_inicio.strip(), timestamp_fin.strip())
    else:
        df_recorte = filtrar_por_minuto(df, start_min, end_min)

    # --- Mapa combinado: track original + track recortado ---
    st.subheader("🗺️ Visualización comparada: original (gris) y recorte (rojo)")

    # Track original (gris)
    line_data_full = []
    for i in range(1, len(df)):
        p1 = df.iloc[i - 1]
        p2 = df.iloc[i]
        line_data_full.append({
            "from": [p1['lon'], p1['lat']],
            "to": [p2['lon'], p2['lat']],
            "color": [160, 160, 160]  # gris
        })

    # Track recortado (rojo)
    line_data_rec = []
    if not df_recorte.empty:
        for i in range(1, len(df_recorte)):
            p1 = df_recorte.iloc[i - 1]
            p2 = df_recorte.iloc[i]
            line_data_rec.append({
                "from": [p1['lon'], p1['lat']],
                "to": [p2['lon'], p2['lat']],
                "color": [220, 20, 60]  # rojo fuerte
            })

    layers = [
        pdk.Layer(
            'LineLayer',
            data=line_data_full,
            get_source_position='from',
            get_target_position='to',
            get_color='color',
            get_width=3,
            pickable=False,
            name="Track original"
        )
    ]
    if line_data_rec:
        layers.append(
            pdk.Layer(
                'LineLayer',
                data=line_data_rec,
                get_source_position='from',
                get_target_position='to',
                get_color='color',
                get_width=4,
                pickable=False,
                name="Track recortado"
            )
        )
        # Puntos de inicio y fin del recorte
        layers += [
            pdk.Layer('ScatterplotLayer',
                data=[{"lat": df_recorte.iloc[0]['lat'], "lon": df_recorte.iloc[0]['lon'], "name": "Inicio recorte"}],
                get_position='[lon, lat]',
                get_color='[0, 255, 0]',  # verde: inicio recorte
                get_radius=30,
                pickable=True,
            ),
            pdk.Layer('ScatterplotLayer',
                data=[{"lat": df_recorte.iloc[-1]['lat'], "lon": df_recorte.iloc[-1]['lon'], "name": "Fin recorte"}],
                get_position='[lon, lat]',
                get_color='[255, 0, 0]',  # rojo: fin recorte
                get_radius=30,
                pickable=True,
            )
        ]

    # Centro del mapa
    lat_center = df_recorte['lat'].mean() if not df_recorte.empty else df['lat'].mean()
    lon_center = df_recorte['lon'].mean() if not df_recorte.empty else df['lon'].mean()

    # Leyenda manual
    st.markdown("""
    <div style='display:flex;gap:30px;align-items:center;font-size:16px;'>
      <span style='display:inline-flex;align-items:center;'>
        <span style='display:inline-block;width:30px;height:10px;background:#a0a0a0;margin-right:8px;'></span>
        Track original
      </span>
      <span style='display:inline-flex;align-items:center;'>
        <span style='display:inline-block;width:30px;height:10px;background:#dc143c;margin-right:8px;'></span>
        Track recortado
      </span>
      <span style='display:inline-flex;align-items:center;'>
        <span style='display:inline-block;width:16px;height:16px;background:#00ff00;border-radius:50%;margin-right:4px;'></span>
        Inicio recorte
      </span>
      <span style='display:inline-flex;align-items:center;'>
        <span style='display:inline-block;width:16px;height:16px;background:#ff0000;border-radius:50%;margin-right:4px;'></span>
        Fin recorte
      </span>
    </div>
    """, unsafe_allow_html=True)

    st.pydeck_chart(pdk.Deck(
        map_style=map_style,
        initial_view_state=pdk.ViewState(
            latitude=lat_center,
            longitude=lon_center,
            zoom=13,
            pitch=0,
            # bearing=0  # ¿Agregar orientación por futuro TWD?
        ),
        layers=layers,
        tooltip={"html": "<b>Track</b>"}  # Tooltip simple en los puntos de inicio/fin
    ))

    # --- Información básica del recorte ---
    st.subheader("✂️ Info del tramo recortado")
    if not df_recorte.empty:
        st.markdown(f"**Inicio recorte:** {df_recorte['time'].iloc[0]}")
        st.markdown(f"**Fin recorte:** {df_recorte['time'].iloc[-1]}")
        st.markdown(f"**Cantidad de puntos:** {len(df_recorte)}")
        st.markdown(f"**Duración recorte:** {df_recorte['time'].iloc[-1] - df_recorte['time'].iloc[0]}")
    else:
        st.warning("El tramo seleccionado no contiene puntos. Ajusta el filtro.")

    # --- Input de nombre de archivo destino y exportar ---
    st.subheader("💾 Exportar GPX recortado")
    base_name = os.path.splitext(uploaded_file.name)[0] if uploaded_file else "recorte-maxsail"
    file_name = st.text_input("Nombre del archivo a guardar (sin extensión)", value=f"{base_name}-recorte")
    if not df_recorte.empty:
        gpx_output = df_to_gpx(df_recorte)
        st.download_button(
            label="📥 Descargar archivo GPX",
            data=gpx_output,
            file_name=f"{file_name}.gpx",
            mime="application/gpx+xml"
        )
else:
    st.info("Sube un archivo GPX, VKX o FIT para comenzar.")

# --- DATOS DE CONTACTO Y DISCLAIMER ---
st.markdown("""
---
#### 📢 Proyecto abierto y descargo de responsabilidad

Este visor de regatas es un proyecto abierto y experimental, creado con el objetivo de compartir, comparar y analizar tracks GPS de forma colaborativa en la flota.

**Creador / Author:**  
- Maximiliano Mannise  
- [maxsail.project@gmail.com](mailto:maxsail.project@gmail.com)  
- [GitHub: maxsail-project](https://github.com/maxsail-project)  

**Aviso legal / Disclaimer:**  
La información visualizada y los análisis generados por esta herramienta son orientativos y no deben ser considerados como asesoramiento profesional ni como datos oficiales de regatas. El creador no asume ninguna responsabilidad por el uso, interpretación o decisiones tomadas a partir de la información mostrada.

El código es de uso libre y puede ser compartido, modificado y distribuido bajo los términos de la licencia MIT.  
¡Cualquier mejora, comentario o contribución es bienvenida!
""")

with st.sidebar:
    st.markdown("""
    **maxSail-analytics**
    - Autor: Maximiliano Mannise
    - [maxsail.project@gmail.com](mailto:maxsail.project@gmail.com)
    - [GitHub: maxsail-project](https://github.com/maxsail-project)
    """)

with st.sidebar:
    st.markdown("---")
    st.markdown("**Versión:** v1.2.0  \n[Changelog](https://github.com/maxsail-project/maxsail-analytics/blob/main/CHANGELOG.md)")
