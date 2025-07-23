import streamlit as st
import gpxpy
import pandas as pd
import pydeck as pdk
from datetime import datetime, timedelta
import os

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

# --- Sidebar: subir archivo GPX ---
uploaded_file = st.sidebar.file_uploader(
    "📂 Selecciona un archivo GPX", 
    type="gpx",
    accept_multiple_files=False
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

# --- Main ---
if uploaded_file:
    gpx = gpxpy.parse(uploaded_file)
    df = gpx_to_df(gpx)
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    total_duration = (df['time'].iloc[-1] - df['time'].iloc[0]).total_seconds() / 60

    # --- Sidebar: filtros de inicio/fin (en minutos y segundos) ---
    st.sidebar.header("🎚️ Selección de tramo")
    min_duration = int(total_duration)
    min_ini = st.sidebar.number_input("Minuto inicial", min_value=0, max_value=min_duration, value=0, step=1)
    sec_ini = st.sidebar.number_input("Segundo inicial", min_value=0, max_value=59, value=0, step=5)
    min_fin = st.sidebar.number_input("Minuto final", min_value=0, max_value=min_duration, value=min_duration, step=1)
    sec_fin = st.sidebar.number_input("Segundo final", min_value=0, max_value=59, value=0, step=5)
    start_min = min_ini + sec_ini / 60
    end_min = min_fin + sec_fin / 60
    start_min, end_min = st.sidebar.slider(
        "Tramo seleccionado (minutos decimales)",
        0.0, float(total_duration),
        (start_min, end_min),
        step=0.5
    )

    # --- Panel principal: información del track ---
    st.header("🧭 Información del track original")
    meta = get_gpx_metadata(gpx, df)
    meta["Archivo original"] = uploaded_file.name
    meta_df = pd.DataFrame([meta]).T
    meta_df.columns = ['Valor']
    st.table(meta_df)

    # --- Recorte según tramo seleccionado ---
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
        <span style='display:inline-block;width:30px;height:6px;background:#a0a0a0;margin-right:8px;'></span>
        Track original
      </span>
      <span style='display:inline-flex;align-items:center;'>
        <span style='display:inline-block;width:30px;height:6px;background:#dc143c;margin-right:8px;'></span>
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
    st.info("Sube un archivo GPX para comenzar.")

with st.sidebar:
    st.markdown("""
    **maxsail-GPX-cutter**
    - Autor: Maximiliano Mannise
    - [maxsail.project@gmail.com](mailto:maxsail.project@gmail.com)
    - [GitHub](https://github.com/maxsail-project)
    """)
