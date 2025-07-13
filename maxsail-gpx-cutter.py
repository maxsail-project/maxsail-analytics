import streamlit as st
import gpxpy
import pandas as pd
import pydeck as pdk
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="maxSail GPX Cutter", layout="wide")
st.title("⛵ maxSail GPX Cutter")

# --- Sidebar: subir archivo GPX ---
uploaded_file = st.sidebar.file_uploader("📂 Subí tu archivo GPX", type="gpx")

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
    # Slider de tramo (como analytics)
    start_min, end_min = st.sidebar.slider(
        "Tramo seleccionado (minutos decimales)",
        0.0, float(total_duration),
        (start_min, end_min),
        step=0.5
    )

    # --- Panel principal: información del track ---
    st.header("🧭 Información del track original")
    meta = get_gpx_metadata(gpx, df)
    meta["Archivo original"] = uploaded_file.name  # <-- nombre del archivo subido
    meta_df = pd.DataFrame([meta]).T
    meta_df.columns = ['Valor']
    st.table(meta_df)


    # --- Mapa del track completo (sin tiles) ---
    st.subheader("🗺️ Vista previa del track completo")
    line_data_full = []
    for i in range(1, len(df)):
        p1 = df.iloc[i - 1]
        p2 = df.iloc[i]
        line_data_full.append({
            "from": [p1['lon'], p1['lat']],
            "to": [p2['lon'], p2['lat']],
            "color": [0, 100, 255]
        })
    layers_full = [
        pdk.Layer('LineLayer',
            data=line_data_full,
            get_source_position='from',
            get_target_position='to',
            get_color='color',
            get_width=3
        ),
        pdk.Layer('ScatterplotLayer',
            data=[{"lat": df.iloc[0]['lat'], "lon": df.iloc[0]['lon']}],
            get_position='[lon, lat]',
            get_color='[0, 255, 0]',  # verde: inicio
            get_radius=20
        ),
        pdk.Layer('ScatterplotLayer',
            data=[{"lat": df.iloc[-1]['lat'], "lon": df.iloc[-1]['lon']}],
            get_position='[lon, lat]',
            get_color='[255, 0, 0]',  # rojo: fin
            get_radius=20
        )
    ]
    st.pydeck_chart(pdk.Deck(
        #map_style=None,
        map_style="mapbox://styles/mapbox/outdoors-v11",
        initial_view_state=pdk.ViewState(
            latitude=df['lat'].mean(),
            longitude=df['lon'].mean(),
            zoom=13,
            pitch=0,
        ),
        layers=layers_full
    ))

    # --- Recorte según tramo seleccionado ---
    df_recorte = filtrar_por_minuto(df, start_min, end_min)

    # --- Mapa del track recortado ---
    st.subheader("✂️ Track recortado (previo a exportar)")
    if not df_recorte.empty:
        line_data = []
        for i in range(1, len(df_recorte)):
            p1 = df_recorte.iloc[i - 1]
            p2 = df_recorte.iloc[i]
            line_data.append({
                "from": [p1['lon'], p1['lat']],
                "to": [p2['lon'], p2['lat']],
                "color": [255, 100, 0]
            })
        layers = [
            pdk.Layer('LineLayer',
                data=line_data,
                get_source_position='from',
                get_target_position='to',
                get_color='color',
                get_width=3
            ),
            pdk.Layer('ScatterplotLayer',
                data=[{"lat": df_recorte.iloc[0]['lat'], "lon": df_recorte.iloc[0]['lon']}],
                get_position='[lon, lat]',
                get_color='[0, 255, 0]',  # verde: inicio
                get_radius=20
            ),
            pdk.Layer('ScatterplotLayer',
                data=[{"lat": df_recorte.iloc[-1]['lat'], "lon": df_recorte.iloc[-1]['lon']}],
                get_position='[lon, lat]',
                get_color='[255, 0, 0]',  # rojo: fin
                get_radius=20
            )
        ]
        st.pydeck_chart(pdk.Deck(
            #map_style=None,
             map_style="mapbox://styles/mapbox/outdoors-v11",
            initial_view_state=pdk.ViewState(
                latitude=df_recorte['lat'].mean(),
                longitude=df_recorte['lon'].mean(),
                zoom=13,
                pitch=0
            ),
            layers=layers
        ))
        # --- Información básica del recorte ---
        st.markdown(f"**Inicio recorte:** {df_recorte['time'].iloc[0]}")
        st.markdown(f"**Fin recorte:** {df_recorte['time'].iloc[-1]}")
        st.markdown(f"**Cantidad de puntos:** {len(df_recorte)}")
        st.markdown(f"**Duración recorte:** {df_recorte['time'].iloc[-1] - df_recorte['time'].iloc[0]}")
    else:
        st.warning("El tramo seleccionado no contiene puntos. Ajusta el filtro.")

    # --- Input de nombre de archivo destino y exportar ---
    st.subheader("💾 Exportar GPX recortado")
    # Suponiendo que 'uploaded_file.name' tiene el nombre original
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
