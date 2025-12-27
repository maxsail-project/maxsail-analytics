"""
Visor-diff: Sailing Data, Better Decisions
Copyright (c) 2024-2025 Maximiliano Mannise

Licencia / License: MIT (ver LICENSE)

Este proyecto es open source y libre de uso.
Puedes copiar, modificar y compartir el código bajo los términos de la licencia MIT.
The project is open source and free to use.
You can copy, modify and share the code under the terms of the MIT License.

Contacto / Contact:
- Name: Maximiliano Mannise
- Email: maxsail.project@gmail.com
- GitHub: https://github.com/maxsail-project 
"""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import pydeck as pdk
import json

from scipy.stats import circstd, circmean

from utils import (
    distance_on_axis, 
    gpx_file_to_df,
    linea_perpendicular_pyproj,
    puntos_perpendiculares_pyproj,
    calcular_twa_vmg,
    ladder_distance_rung,
    circular_modes_deg,
    sog_modes
)

def mean_circ_signed_deg(series):
    s = pd.to_numeric(series, errors='coerce').dropna()
    if s.empty:
        return np.nan
    return float(circmean(s, high=180, low=-180))


# -----------------------------
# INICIO APP STREAMLIT
# -----------------------------
st.set_page_config(page_title="maxSail-analytics: Visor de regata GPX/CSV", layout="wide")
st.title("🚩 maxSail : Sailing Data, Better Decisions")

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
uploaded_files = st.sidebar.file_uploader(
    "📂 Selecciona uno o más archivos GPX o CSV", 
    type=["gpx", "csv"], 
    accept_multiple_files=True
)

meta_file = st.sidebar.file_uploader(
    "📄 (Opcional) Meta-data JSON",
    type=["json"],
    accept_multiple_files=False
)
meta_data = {}
if meta_file is not None:
    try:
        meta_data = json.load(meta_file)
    except Exception as e:
        st.sidebar.error(f"Error leyendo meta-data JSON: {e}")

if not uploaded_files:
    st.info("Sube al menos un archivo GPX o CSV para comenzar.")
    st.markdown("""

    **maxSail-analytics** es una herramienta open source para visualizar, analizar y comparar tracks GPS de regatas y entrenamientos de vela. Permite cargar archivos GPX o CSV, mostrar recorridos en mapa, comparar dos tracks, analizar métricas clave y detectar maniobras, todo de forma sencilla y colaborativa.

    **maxSail-analytics** is an open source tool to visualize, analyze and compare GPS tracks from sailing races and training. You can load GPX or CSV files, display tracks on an interactive map, compare two routes, analyze key metrics, and detect maneuvers—everything simply and collaboratively.

    ---

    ### Características principales / Main features

    - Visualización de tracks en mapa interactivo.  
    *Interactive track display on a map.*
    - Comparación de dos recorridos lado a lado.  
    *Side-by-side comparison of two routes.*
    - Análisis de velocidad, rumbo, TWA, VMG y distancia recorrida.  
    *Analysis of speed, heading (COG), TWA, VMG, and distance sailed.*
    - Detección automática de maniobras (viradas/trasluchadas).  
    *Automatic maneuver detection (tacks/gybes).*
    - Cálculo y visualización de métricas clave.  
    *Calculation and visualization of key metrics.*
    - Compatible con archivos GPX y CSV normalizados.  
    *Compatible with normalized GPX and CSV files.*
    - Interfaz intuitiva, lista para compartir con la flota.  
    *Intuitive interface, ready to share with your fleet.*
    - **Open source y multiplataforma.**  
    ***Open source and cross-platform.***

    ---

    ### Formato esperado del archivo CSV / Expected CSV format

    El visor requiere archivos CSV normalizados con al menos estas columnas:  
    *The viewer requires normalized CSV files with at least these columns:*

    - **Lat, Lon, UTC, COG, SOG, Dist, SourceFile (optional)** [more info](https://github.com/maxsail-project/maxsail-analytics/blob/main/README.md#formato-esperado-del-archivo-csv--expected-csv-format)

    ---

    ### Contacto / Contact

    - Nombre / Name: Maximiliano Mannise  
    - Email: maxsail.project@gmail.com  
    - GitHub: https://github.com/maxsail-project/maxsail-analytics  

    ---

    *Este proyecto es open source, ¡colaboraciones y sugerencias bienvenidas!*  
    *This project is open source — contributions and feedback are welcome!*

    © 2024-2025 Maximiliano Mannise / maxsail-project
    """)
    st.stop()


dfs = []
for file in uploaded_files:
    if file.name.lower().endswith('.csv'):
        df = pd.read_csv(file, delimiter=',')
        if not all(col in df.columns for col in ['Lat', 'Lon', 'UTC', 'COG', 'SOG', 'Dist']):
            st.warning(f"El archivo {file.name} no tiene columnas requeridas.")
            continue
        if not np.issubdtype(df['UTC'].dtype, np.datetime64):
            df['UTC'] = pd.to_datetime(df['UTC'])
        if "SourceFile" not in df.columns:
            df["SourceFile"] = file.name
        dfs.append(df)
    elif file.name.lower().endswith('.gpx'):
        df = gpx_file_to_df(file, file.name)
        if not df.empty:
            dfs.append(df)
if not dfs:
    st.error("No se encontraron tracks válidos.")
    st.stop()

df = pd.concat(dfs, ignore_index=True)

# --- Comprobación de coincidencia con ARCHIVO_TRACK (si existe) ---
if meta_data.get("ARCHIVO_TRACK"):
    esperado = str(meta_data["ARCHIVO_TRACK"]).strip()
    try:
        archivos_subidos = [f.name for f in uploaded_files]
        if esperado and archivos_subidos and all(esperado != n for n in archivos_subidos):
            #st.sidebar.warning(f"El meta-data sugiere '{esperado}', pero los archivos cargados son: {', '.join(archivos_subidos)}")
            st.sidebar.warning("Fichero de metadatos con nombre distinto a tracks")
    except Exception:
        pass


# --- Selección de tracks ---
if "SourceFile" in df.columns:
    track_files = sorted(df['SourceFile'].dropna().unique().tolist(), reverse=True)
    track_choices = ["(Ninguno)"] + track_files
    track1 = st.sidebar.selectbox("Track 1:", track_choices, index=1 if len(track_files) > 0 else 0)
    track2 = st.sidebar.selectbox("Track 2:", track_choices, index=0)
else:
    track_files = ["Track único"]
    track1 = track2 = "Track único"
    df["SourceFile"] = "Track único"

df1          = df[df['SourceFile'] == track1].copy() if track1 != "(Ninguno)" else pd.DataFrame()
df2          = df[df['SourceFile'] == track2].copy() if track2 != "(Ninguno)" else pd.DataFrame()
#df1_original = df[df['SourceFile'] == track1].copy() if track1 != "(Ninguno)" else pd.DataFrame()
#df2_original = df[df['SourceFile'] == track2].copy() if track2 != "(Ninguno)" else pd.DataFrame()
df1_sync     = df[df['SourceFile'] == track1].copy() if track1 != "(Ninguno)" else pd.DataFrame()
df2_sync     = df[df['SourceFile'] == track2].copy() if track2 != "(Ninguno)" else pd.DataFrame()

if df1.empty and df2.empty:
    st.info("Selecciona al menos un track para comenzar.")
    st.stop()

# --- Sincronizar tiempos entre ambos tracks ---
if not df1.empty and not df2.empty and "UTC" in df1.columns and "UTC" in df2.columns:

    # --- Sincronizar inicio ---
    t0_sync = max(df1["UTC"].iloc[0], df2["UTC"].iloc[0])
    df1_sync = df1[df1["UTC"] >= t0_sync].copy().reset_index(drop=True)
    df2_sync = df2[df2["UTC"] >= t0_sync].copy().reset_index(drop=True)

    if df1_sync.empty or df2_sync.empty:
        st.warning("No hay tramo común tras sincronizar por UTC. Imposible comparar tracks.")
        st.stop()
    else:
        # --- Sincronizar fin ---
        tf_sync = min(df1_sync["UTC"].iloc[-1], df2_sync["UTC"].iloc[-1])
        df1_sync = df1_sync[df1_sync["UTC"] <= tf_sync].copy()
        df2_sync = df2_sync[df2_sync["UTC"] <= tf_sync].copy()
        # --- Recalcular minutos desde t0 común ---
        t0 = t0_sync
        df1_sync["minutes"] = (df1_sync["UTC"] - t0).dt.total_seconds() / 60
        df2_sync["minutes"] = (df2_sync["UTC"] - t0).dt.total_seconds() / 60
        # --- Sustituir dataframes base ---
        df1 = df1_sync
        df2 = df2_sync

# --- Ingreso manual de TWD ---
twd = st.sidebar.number_input(
    "TWD True Wind Direction (º) estimada", min_value=0, max_value=360, value=int(meta_data.get("TWD", 0)), step=5
)
# --- Ingreso manual de minuto de salida ---
minuto_salida = st.sidebar.number_input(
    "Minuto de salida", min_value=0, max_value=10, value=int(meta_data.get("MINUTO_SALIDA", 0)), step=1,
)

# --- Calcular duración mínima ---
if not df1.empty and not df2.empty:
    dur1 = (df1['UTC'].iloc[-1] - df1['UTC'].iloc[0]).total_seconds() / 60
    dur2 = (df2['UTC'].iloc[-1] - df2['UTC'].iloc[0]).total_seconds() / 60
    min_duration = min(dur1, dur2)
elif not df1.empty:
    min_duration = (df1['UTC'].iloc[-1] - df1['UTC'].iloc[0]).total_seconds() / 60
elif not df2.empty:
    min_duration = (df2['UTC'].iloc[-1] - df2['UTC'].iloc[0]).total_seconds() / 60
else:
    min_duration = 0.0

min_duration = int(min_duration)

if "last_track1" not in st.session_state or st.session_state["last_track1"] != track1 or st.session_state["last_track2"] != track2:
    st.session_state["start_min"] = 0.0
    st.session_state["end_min"] = float(min_duration)
    st.session_state["last_track1"] = track1
    st.session_state["last_track2"] = track2

min_ini = int(st.session_state["start_min"])
sec_ini = 0
min_fin = int(st.session_state["end_min"])
sec_fin = 0

st.sidebar.markdown("---")
st.sidebar.markdown("**Tramo temporal**")

# Selector de minutos (inicio / fin)
min_ini, min_fin = st.sidebar.slider(
    "Minutos",
    0,
    int(min_duration),
    (min_ini, min_fin),
    step=1
)

# Ajuste fino en segundos
sec_ini = st.sidebar.number_input(
    "Segundo inicial",
    min_value=0,
    max_value=59,
    value=sec_ini,
    step=10
)

sec_fin = st.sidebar.number_input(
    "Segundo final",
    min_value=0,
    max_value=59,
    value=sec_fin,
    step=10
)

# Conversión a minutos decimales
def to_minutes(mins, secs):
    return mins + secs / 60.0

start_min = to_minutes(min_ini, sec_ini)
end_min   = to_minutes(min_fin, sec_fin)

# Protección contra tramo inválido
if end_min <= start_min:
    end_min = min(start_min + 1.0, float(min_duration))

# --- Filtrar por tiempo ---
def filtrar_por_tiempo(df, start_min, end_min):
    t0 = df['UTC'].iloc[0]
    df = df.copy()
    df['minutes'] = (df['UTC'] - t0).dt.total_seconds() / 60
    return df[(df['minutes'] >= start_min) & (df['minutes'] <= end_min)].copy()

# --- Calcular frecuencia promedio ---
def calcular_frecuencia(df):
    if df.empty or len(df) < 2:
        return "-"
    dur_sec = (df['UTC'].iloc[-1] - df['UTC'].iloc[0]).total_seconds()
    if dur_sec <= 0:
        return "-"
    return f"{len(df) / dur_sec:.2f}"

# --- Calcular TWA y VMG ---
if not df1.empty:
    df1 = filtrar_por_tiempo(df1, start_min, end_min)
    df1 = calcular_twa_vmg(df1, twd)
if not df2.empty:
    df2 = filtrar_por_tiempo(df2, start_min, end_min)
    df2 = calcular_twa_vmg(df2, twd)

if df1.empty and df2.empty:
    st.warning("El tramo seleccionado no contiene datos en uno o ambos tracks. Ajusta el tramo para ver los análisis.")
    st.stop()

# --- MAPA: Visualización comparada ---

# Calcula el SOG promedio total de cada track
sog_avg_azul = round(df1['SOG'].mean(), 2) if not df1.empty else 0
sog_avg_naranja = round(df2['SOG'].mean(), 2) if not df2.empty else 0

st.subheader("📍 Mapa - visualización de tracks")
layers = []

def line_segments(df):
    segments = []
    for i in range(1, len(df)):
        p1 = df.iloc[i - 1]
        p2 = df.iloc[i]
        segments.append({
            "from": [p1["Lon"], p1["Lat"]],
            "to":   [p2["Lon"], p2["Lat"]],
        })
    return segments


# --- Track 1 completo (azul) ---
if not df1_sync.empty:
    layers.append(
        pdk.Layer(
            "LineLayer",
            data=line_segments(df1_sync),
            get_source_position="from",
            get_target_position="to",
            get_color="[0, 100, 255, 80]",  # azul, MUY transparente
            get_width=1,
            pickable=False,
            name="Track 1 completo",
        )
    )

# --- Track 2 completo (naranja) ---
if not df2_sync.empty:
    layers.append(
        pdk.Layer(
            "LineLayer",
            data=line_segments(df2_sync),
            get_source_position="from",
            get_target_position="to",
            get_color="[255, 100, 0, 80]",  # naranja, MUY transparente
            get_width=1,
            pickable=False,
            name="Track 2 completo",
        )
    )

if not df1.empty:
    line_data1 = []
    for i in range(1, len(df1)):
        p1 = df1.iloc[i - 1]
        p2 = df1.iloc[i]
        line_data1.append({
            "from": [p1['Lon'], p1['Lat']],
            "to": [p2['Lon'], p2['Lat']],
            "color": [0, 100, 255],
            "SOG_avg": sog_avg_azul  # <<< Aquí agregas el SOG promedio global
        })
    layers.append(
        pdk.Layer(
            'LineLayer',
            data=line_data1,
            get_source_position='from',
            get_target_position='to',
            get_color='color',
            get_width=4,
            pickable=True,  # Necesario para tooltips
        )
    )
    # Inicio (azul)
    layers.append(
        pdk.Layer(
            'ScatterplotLayer',
            data=[{"Latitude": df1.iloc[0]['Lat'], "Longitude": df1.iloc[0]['Lon'], "name": "Inicio Track 1"}],
            get_position='[Longitude, Latitude]',
            get_color='[0, 0, 0]',
            get_radius=5,
            pickable=True,
        )
    )
    # Fin (azul)
    layers.append(
        pdk.Layer(
            'ScatterplotLayer',
            data=[{"Latitude": df1.iloc[-1]['Lat'], "Longitude": df1.iloc[-1]['Lon'], "name": "Fin Track 1"}],
            get_position='[Longitude, Latitude]',
            get_color='[0, 100, 255]',
            get_radius=5,
            pickable=True,
        )
    )

# --- Track 2 (naranja) ---
if not df2.empty:
    line_data2 = []
    for i in range(1, len(df2)):
        p1 = df2.iloc[i - 1]
        p2 = df2.iloc[i]
        line_data2.append({
            "from": [p1['Lon'], p1['Lat']],
            "to": [p2['Lon'], p2['Lat']],
            "color": [255, 100, 0],
            "SOG_avg": sog_avg_naranja
        })
    layers.append(
        pdk.Layer(
            'LineLayer',
            data=line_data2,
            get_source_position='from',
            get_target_position='to',
            get_color='color',
            get_width=4,
            pickable=True,
        )
    )
    # Inicio (naranja)
    layers.append(
        pdk.Layer(
            'ScatterplotLayer',
            data=[{"Latitude": df2.iloc[0]['Lat'], "Longitude": df2.iloc[0]['Lon'], "name": "Inicio Track 2"}],
            get_position='[Longitude, Latitude]',
            get_color='[0, 0, 0]',
            get_radius=5,
            pickable=True,
        )
    )
    # Fin (naranja)
    layers.append(
        pdk.Layer(
            'ScatterplotLayer',
            data=[{"Latitude": df2.iloc[-1]['Lat'], "Longitude": df2.iloc[-1]['Lon'], "name": "Fin Track 2"}],
            get_position='[Longitude, Latitude]',
            get_color='[255, 100, 0]',
            get_radius=5,
            pickable=True,
        )
    )

# --- Balizas desde meta-data (rojas) ---
if meta_data.get("BALIZAS"):
    try:
        bal_meta = pd.DataFrame(meta_data["BALIZAS"])
        # Normalizar nombres de columnas
        if "lat" in bal_meta.columns: bal_meta.rename(columns={"lat": "Lat"}, inplace=True)
        if "lon" in bal_meta.columns: bal_meta.rename(columns={"lon": "Lon"}, inplace=True)
        if "nombre" not in bal_meta.columns: bal_meta["nombre"] = ""
        bal_meta["color"] = [[220, 20, 60] for _ in range(len(bal_meta))]  # rojo

        layer_balizas_meta = pdk.Layer(
            'ScatterplotLayer',
            data=bal_meta,
            get_position='[Lon, Lat]',
            get_color='color',
            get_radius=7,
            pickable=True
        )
        layer_text_balizas = pdk.Layer(
            'TextLayer',
            data=bal_meta,
            get_position='[Lon, Lat]',
            get_text='nombre',
            get_size=16,
            get_color='[0,0,0]',
            get_text_anchor='"middle"',
            get_alignment_baseline='"top"'
        )
        layers.append(layer_balizas_meta)
        layers.append(layer_text_balizas)
    except Exception as e:
        st.warning(f"No se pudieron cargar balizas desde meta-data: {e}")

# --- Calcula el centro del mapa ---
latitudes = []
longitudes = []
if not df1.empty:
    latitudes.append(df1['Lat'].mean())
    longitudes.append(df1['Lon'].mean())
if not df2.empty:
    latitudes.append(df2['Lat'].mean())
    longitudes.append(df2['Lon'].mean())

lat_mean = np.mean(latitudes) if latitudes else 0
lon_mean = np.mean(longitudes) if longitudes else 0

# --- Color scale para ambos tracks ---
color_scale = alt.Scale(
    domain=[f'{track1} (azul)', f'{track2} (naranja)'],
    range=['#0064FF', '#FF6400']
)

# --- Construcción de DataFrame combinado para gráficos ---
if not df1.empty:
    df1_plot = df1.copy()
    df1_plot['Track'] = f'{track1} (azul)'
else:
    df1_plot = pd.DataFrame()
if not df2.empty:
    df2_plot = df2.copy()
    df2_plot['Track'] = f'{track2} (naranja)'
else:
    df2_plot = pd.DataFrame()

if not df1_plot.empty and not df2_plot.empty:
    df_plot = pd.concat([df1_plot, df2_plot])
elif not df1_plot.empty:
    df_plot = df1_plot
elif not df2_plot.empty:
    df_plot = df2_plot
else:
    df_plot = pd.DataFrame()

# --- Cálculo punto central en el minuto_salida ---
punto_salida = None
if not df1_sync.empty:
    df1_temp = df1_sync.copy()
    df1_temp['minutes'] = (df1_temp['UTC'] - df1_temp['UTC'].iloc[0]).dt.total_seconds() / 60
    df_salida = df1_temp[np.abs(df1_temp['minutes'] - minuto_salida) < 0.10]  # tolerancia en minutos
    if not df_salida.empty:
        punto_salida = df_salida.iloc[0]

# --- Calcular puntos perpendiculares si hay punto válido ---
if punto_salida is not None and twd is not None:
    lat0 = punto_salida['Lat']
    lon0 = punto_salida['Lon']
    pt1, pt2 = puntos_perpendiculares_pyproj(lat0, lon0, twd, distancia_m=100)

    # Crear DataFrame con la línea blanca
    linea_blanca = pd.DataFrame([{
        "from": [pt1[1], pt1[0]],  # lon, lat
        "to":   [pt2[1], pt2[0]],  # lon, lat
    }])

    capa_linea_blanca = pdk.Layer(
        'LineLayer',
        data=linea_blanca,
        get_source_position='from',
        get_target_position='to',
        get_color='[255, 255, 255]',
        get_width=4,
        pickable=False
    )

    # --- Añadir puntos blancos al mapa ---
    layers.append(capa_linea_blanca)

# --- Añadir linea en barco azul
if not df1.empty:
    lat_ini1 = df1.iloc[-1]['Lat']
    lon_ini1 = df1.iloc[-1]['Lon']
    pt1a, pt1b = linea_perpendicular_pyproj(lat_ini1, lon_ini1, twd, distancia_m=20)

    data_linea_azul = pd.DataFrame([{
        "from": [pt1a[1], pt1a[0]],
        "to":   [pt1b[1], pt1b[0]],
    }])

    capa_linea_azul = pdk.Layer(
        'LineLayer',
        data=data_linea_azul,
        get_source_position='from',
        get_target_position='to',
        get_color='[0, 100, 255, 128]',  # Azul, 50% transparencia
        get_width=3,
        pickable=False
    )
    layers.append(capa_linea_azul)

# --- Añadir linea en barco naranja ---
if not df2.empty:
    lat_fin2 = df2.iloc[-1]['Lat']
    lon_fin2 = df2.iloc[-1]['Lon']
    pt2a, pt2b = linea_perpendicular_pyproj(lat_fin2, lon_fin2, twd, distancia_m=20)
    data_linea_naranja = pd.DataFrame([{
        "from": [pt2a[1], pt2a[0]],
        "to":   [pt2b[1], pt2b[0]],
    }])
    capa_linea_naranja = pdk.Layer(
        'LineLayer',
        data=data_linea_naranja,
        get_source_position='from',
        get_target_position='to',
        get_color='[255, 100, 0, 128]',
        get_width=3,
        pickable=False
    )
    layers.append(capa_linea_naranja)

# --- Mostrar tracks en el mapa ---
try:
    # --- Muestra el mapa con los tracks ---
    st.markdown(f"""
        <div style='display:flex;gap:30px;align-items:center;font-size:16px;'>
        <span style="display:inline-block;width:30px;height:10px;background:#0064ff;margin-right:8px;margin-bottom:2px;"></span>
        {track1} 
        <span style="display:inline-block;width:30px;height:10px;background:#ff6400;;margin-right:8px;margin-bottom:2px;"></span>
        {track2}
        </div>
        """, unsafe_allow_html=True)

    st.pydeck_chart(pdk.Deck(
        map_style=map_style,
        initial_view_state=pdk.ViewState(
            latitude=lat_mean,
            longitude=lon_mean,
            zoom=14,
            pitch=0,
            bearing=twd
        ),
        layers=layers,
        tooltip={"html": "<b>SOG promedio:</b> {SOG_avg} kn"},
    ))
except Exception as e:
    st.error(f"Error al cargar el mapa: {e}")

# --- BLOQUE PARA CALCULAR Y COMPARAR DISTANCIAS RECORRIDAS ---
if not df1.empty and not df2.empty and twd is not None:
    # INICIO
    lat1_ini, lon1_ini = df1.iloc[0]["Lat"], df1.iloc[0]["Lon"]
    lat2_ini, lon2_ini = df2.iloc[0]["Lat"], df2.iloc[0]["Lon"]
    # FIN
    lat1_fin, lon1_fin = df1.iloc[-1]["Lat"], df1.iloc[-1]["Lon"]
    lat2_fin, lon2_fin = df2.iloc[-1]["Lat"], df2.iloc[-1]["Lon"]

    # --- NUEVO: Distancia entre peldaños a la misma altura sobre el viento (realmente lo que ves como líneas punteadas)
    # Usamos el barco azul como referencia (puedes cambiarlo)
    dist_peldaños_ini = distance_on_axis(lat1_ini, lon1_ini, lat2_ini, lon2_ini, twd)
    dist_peldaños_fin = distance_on_axis(lat1_fin, lon1_fin, lat2_fin, lon2_fin, twd)

    # Opcional: también puedes calcular la separación sobre el eje del viento (avance hacia boya/barlovento/sotavento)
    dist_eje_ini = ladder_distance_rung(lat1_ini, lon1_ini, lat2_ini, lon2_ini, twd)
    dist_eje_fin = ladder_distance_rung(lat1_fin, lon1_fin, lat2_fin, lon2_fin, twd)

    N = 30  # Número de puntos a promediar para inicio y fin
    def tramo_tipo_twa(twa_mean):
        if np.isnan(twa_mean):
            return "None"
        abs_twa = abs(twa_mean)
        if abs_twa < 60:
            return "ceñida"
        else:
            return "popa/través"

    vals_ini = []
    if not df1.empty: vals_ini.append(mean_circ_signed_deg(df1["TWA_abs"].iloc[:N]))
    if not df2.empty: vals_ini.append(mean_circ_signed_deg(df2["TWA_abs"].iloc[:N]))
    twa_ini = np.nanmean(vals_ini) if vals_ini else np.nan

    vals_fin = []
    if not df1.empty: vals_fin.append(mean_circ_signed_deg(df1["TWA_abs"].iloc[-N:]))
    if not df2.empty: vals_fin.append(mean_circ_signed_deg(df2["TWA_abs"].iloc[-N:]))
    twa_fin = np.nanmean(vals_fin) if vals_fin else np.nan

    tipo_tramo_ini = tramo_tipo_twa(twa_ini)
    tipo_tramo_fin = tramo_tipo_twa(twa_fin)

    #--- TABLA COMPARATIVA DE DISTANCIAS EN PUNTO INICIO y FIN
    rows = []
    for pos, tipo, metrica, valor in [
        ("Inicio", tipo_tramo_ini,
         "Dif. de peldaños (barlovento/sotavento)" if tipo_tramo_ini == "ceñida" else "Avance respecto al eje viento",
         dist_peldaños_ini if tipo_tramo_ini == "ceñida" else dist_eje_ini),
        ("Fin", tipo_tramo_fin,
         "Dif. de peldaños (barlovento/sotavento)" if tipo_tramo_fin == "ceñida" else "Avance respecto al eje viento",
         dist_peldaños_fin if tipo_tramo_fin == "ceñida" else dist_eje_fin),
    ]:
        if tipo in ["ceñida", "popa/través"]:
            barco = "Naranja" if valor > 0 else "Azul"
            rows.append({
                "Punto": pos,
                "Tipo": tipo.capitalize(),
                "Barco delante": barco,
                "Distancia (m)": f"{abs(valor):.1f}",
                "Métrica": metrica
            })
        else:
            rows.append({
                "Punto": pos,
                "Tipo": tipo.capitalize(),
                "Barco delante": "-",
                "Distancia (m)": "-",
                "Métrica": "-"
            })

    df_comp = pd.DataFrame(rows)
    st.dataframe(df_comp, use_container_width=True, hide_index=True)

# ----------------------------
# --- MÉTRICAS PRINCIPALES ---
# ----------------------------
st.subheader("📊 Métricas principales del tramo")

metrics = [
    ("TWD* (°)", lambda df: f"{twd:.0f}" if twd is not None else "-"),
    ("SOG promedio (knots)", lambda df: f"{df['SOG'].mean():.2f}" if not df.empty else "-"),
    ("SOG mediana (knots)", lambda df: f"{df['SOG'].median():.2f}" if not df.empty else "-"),  # <-- Nueva línea
    ("SOG máxima (knots)", lambda df: f"{df['SOG'].max():.2f}" if not df.empty else "-"),
    ("TWA* medio (°)", lambda df: f"{mean_circ_signed_deg(df['TWA']):.1f}" if (not df.empty and 'TWA' in df.columns and not df['TWA'].isnull().all()) else "-"),
    ("VMG* promedio (knots)", lambda df: f"{df['VMG'].mean():.2f}" if not df.empty else "-"),
    ("Distancia (nm) (m)", lambda df: f"{df['Dist'].sum() / 1852:.2f} ({int(df['Dist'].sum()):,} m)" if not df.empty else "-"),
    ("Duración (HH:MM:SS)", lambda df: (
        str(pd.to_timedelta((df['UTC'].iloc[-1] - df['UTC'].iloc[0]).total_seconds(), unit='s')).split('.')[0].replace('0 days ', '')
        if not df.empty and len(df) > 1 else "-"
    )),
    ("Frecuencia promedio (Hz)", lambda df: calcular_frecuencia(df)),
]


track_dfs = []
track_labels = []
track_colors = []

if not df1_plot.empty:
    track_dfs.append(df1_plot)
    track_labels.append(f"{track1} (azul)")
    track_colors.append("#0064FF")
if not df2_plot.empty:
    track_dfs.append(df2_plot)
    track_labels.append(f"{track2} (naranja)")
    track_colors.append("#FF6400")
# más tracks en el futuro, agrégarlos aquí.

##### BLOQUE PARA ESCALA DE TIEMPO
# --- Tiempo sincronizado para gráficos (solo tracks seleccionados/visibles) ---
if not df_plot.empty:
    # inicio por track
    starts = []
    for trk in df_plot['Track'].unique():
        t0 = pd.to_datetime(df_plot.loc[df_plot['Track'] == trk, 'UTC']).min()
        if pd.notnull(t0):
            starts.append(t0)
    # t=0 es el inicio común (el más tardío de los inicios visibles)
    if starts:
        sync_start = max(starts)
        df_plot['Elapsed_min'] = (
            pd.to_datetime(df_plot['UTC']) - sync_start
        ).dt.total_seconds() / 60.0

##### LO DE ARRIBA IGUAL SOBRA

# --- Tiempo relativo (t=0 en salida del track azul) ---
if not df_plot.empty:
    # Intentar encontrar el label del track azul
    # 1) Si tus labels incluyen "(azul)" úsalo; si no, toma el primer seleccionado
    try:
        track_azul_label = next(
            (t for t in df_plot['Track'].unique() if "(azul)" in str(t).lower()),
            track_labels[0]
        )
    except Exception:
        track_azul_label = track_labels[0]

    df_azul_plot = df_plot[df_plot['Track'] == track_azul_label]

    if not df_azul_plot.empty:
        # Referencia temporal: minuto de salida del azul si está disponible; si no, primer UTC del azul
        if 'punto_salida' in locals() and punto_salida is not None and 'UTC' in punto_salida:
            salida_azul_utc = pd.to_datetime(punto_salida['UTC'])
        else:
            salida_azul_utc = pd.to_datetime(df_azul_plot['UTC']).min()

        # Columnas de tiempo relativo (pueden ser negativas antes de la salida)
        df_plot['Tiempo_relativo_sec'] = (
            pd.to_datetime(df_plot['UTC']) - salida_azul_utc
        ).dt.total_seconds()

        df_plot['Tiempo_relativo_min'] = df_plot['Tiempo_relativo_sec'] / 60.0


##### FIN BLOQUE PARA ESCALA DE TIEMPO

# --- Construye la tabla base ---
tabla_metricas = {}
for label, df in zip(track_labels, track_dfs):
    valores = [calc(df) for _, calc in metrics]
    tabla_metricas[label] = valores

tabla_metricas_df = pd.DataFrame(tabla_metricas, index=[m[0] for m in metrics])

# Calcula distancias recorridas
dist_metros = [df['Dist'].sum() if not df.empty else np.nan for df in track_dfs]
dist_min = np.nanmin(dist_metros)

# Calcula diferencia con mínima distancia para cada track
diferencias = []
for i, dist in enumerate(dist_metros):
    if np.isnan(dist):
        diferencias.append("-")
    else:
        valor = dist - dist_min
        if np.isclose(valor, 0):
            diferencias.append("0 (mínimo)")
        else:
            diferencias.append(f"{valor:,.1f} m")

#  Añade fila de diferencia con minima distancia a la tabla
tabla_metricas_df.loc["Metros extra recorridos (comparado con el otro) (m)"] = diferencias
# --- FECHAS DE INICIO Y FIN ---
min_fechas = []
max_fechas = []
for df in track_dfs:
    if not df.empty:
        min_fechas.append(df['UTC'].min().strftime("%Y-%m-%d %H:%M:%S"))
        max_fechas.append(df['UTC'].max().strftime("%Y-%m-%d %H:%M:%S"))
    else:
        min_fechas.append("-")
        max_fechas.append("-")

tabla_metricas_df.loc["Fecha/Hora inicio"] = min_fechas
tabla_metricas_df.loc["Fecha/Hora fin"] = max_fechas

# --- Formato visual (color de encabezados) ---
styled = tabla_metricas_df.style
for label, color in zip(track_labels, track_colors):
    styled = styled.set_properties(subset=[label], **{'color': color, 'font-weight': 'bold'})

#st.markdown("#### Comparativa por Track")
#st.dataframe(styled, use_container_width=True) # tabla con metricas de tracks
#st.caption("* TWA y VMG calculados según el TWD")

# --- Meta-data (si disponible) ---
if meta_data:
    partes = ["META DATA"]
    if "TWD" in meta_data:
        partes.append(f"TWD: {meta_data['TWD']}°")
    if "TWDShift" in meta_data:
        partes.append(f"TWD Shift to: {meta_data['TWDShift']}°")
    if "TWS" in meta_data:
        partes.append(f"TWS: {meta_data['TWS']} kn")
    if "TWSG" in meta_data:
        partes.append(f"TWSG: {meta_data['TWSG']} kn")
    if "NOTAS" in meta_data and meta_data["NOTAS"]:
        partes.append(f"Notas: {meta_data['NOTAS']}")
    if partes:
        st.info(" | ".join(partes))
else:
    st.info(twd is not None and f"TWD estimada: {twd}°" or "TWD no especificada.")

# =========================================================
# 🧭 TABLA RESUMEN DEFINITIVA DEL TRAMO
# =========================================================

def fmt(val, nd=2):
    return "-" if pd.isna(val) else f"{val:.{nd}f}"

def fmt_delta(val, nd=2):
    return "" if pd.isna(val) else f" ({val:+.{nd}f})"

resumen = {}
dist_vals = {}
eff_vals = {}
sog_vals = {}
cog_modes_vals = {}

for label, df in zip(track_labels, track_dfs):

    if df.empty:
        resumen[label] = ["-"] * 6
        dist_vals[label] = eff_vals[label] = sog_vals[label] = np.nan
        cog_modes_vals[label] = ("-", "-")
        continue

    # --- Distancia recorrida (m) ---
    dist_rec = df["Dist"].sum()
    dist_vals[label] = dist_rec

    # --- Distancia efectiva (integrando VMG) ---
    dt = df["UTC"].diff().dt.total_seconds().fillna(0)
    dist_eff = np.sum(np.abs(df["VMG"]) * 0.51444 * dt)

    # --- Eficiencia ---
    eff = dist_eff / dist_rec if dist_rec > 0 else np.nan
    eff_vals[label] = eff

    # --- SOG ---
    sog_avg = df["SOG"].mean()
    sog_vals[label] = sog_avg

    # --- COG dominantes ---
    modes = circular_modes_deg(
        df["COG"], 
        bin_size=10, #<<-- Ajusta el tamaño de bin si quieres más o menos resolución
        top_n=2)
    cog1 = f"{modes[0][0]:.0f}° ({modes[0][1]:.0f}%)" if len(modes) > 0 else "-"
    cog2 = f"{modes[1][0]:.0f}° ({modes[1][1]:.0f}%)" if len(modes) > 1 else "-"
    cog_modes_vals[label] = (cog1, cog2)

    resumen[label] = [
        fmt(dist_rec, 0),
        fmt(dist_eff, 0),
        fmt(eff, 2),
        fmt(sog_avg, 2),
        cog1,
        cog2,
    ]

# --- Añadir deltas si hay dos barcos ---
if len(track_labels) == 2:
    l1, l2 = track_labels

    resumen[l1][0] += fmt_delta(dist_vals[l1] - dist_vals[l2], 0)
    resumen[l2][0] += fmt_delta(dist_vals[l2] - dist_vals[l1], 0)

    resumen[l1][1] += fmt_delta((eff_vals[l1] - eff_vals[l2]) * dist_vals[l1], 0)
    resumen[l2][1] += fmt_delta((eff_vals[l2] - eff_vals[l1]) * dist_vals[l2], 0)

    resumen[l1][2] += fmt_delta(eff_vals[l1] - eff_vals[l2], 2)
    resumen[l2][2] += fmt_delta(eff_vals[l2] - eff_vals[l1], 2)

    resumen[l1][3] += fmt_delta(sog_vals[l1] - sog_vals[l2], 2)
    resumen[l2][3] += fmt_delta(sog_vals[l2] - sog_vals[l1], 2)

# --- Construir DataFrame final ---
tabla_tramo = pd.DataFrame(
    resumen,
    index=[
        "Distancia recorrida (m)",
        "Distancia efectiva (m)",
        "Eficiencia del tramo",
        "SOG promedio (kn)",
        "COG dominante 1",
        "COG dominante 2",
    ],
)

st.dataframe(tabla_tramo, use_container_width=True)

st.caption(
    "Eficiencia = distancia efectiva / distancia recorrida. "
    "Δ positivos indican mejor rendimiento relativo. "
    "COG dominantes muestran los rumbos más repetidos en el tramo."
    "La distancia efectiva se calcula integrando el VMG estimado a partir del TWD. "
    "El VMG no es una lectura directa del GPS, sino una magnitud derivada (SOG + COG + TWD). "
    "La eficiencia refleja qué parte de la distancia navegada contribuye realmente al avance hacia el objetivo."
    "Valores más altos indican navegación más directa. En ceñida: 0.55 – 0.75. En popa: 0.70 – 0.90"
)


# --- EVOLUCIÓN DE SOG ---
st.divider()
st.subheader("📈 Evolución de SOG (knots)")
if not df_plot.empty:
    # --- Línea vertical en minuto de salida ---
    linea_salida = alt.Chart(pd.DataFrame({'Tiempo_relativo_min': [0]})).mark_rule(
        color='black',
        strokeDash=[4, 4],
        size=2
    ).encode(
        x='Tiempo_relativo_min:Q'
    )

    # --- Gráfico de SOG ---
    chart_sog = alt.Chart(df_plot).mark_line(opacity=0.9).encode(
        x=alt.X('UTC:T', title='Hora GPS'),
        #x=alt.X('Tiempo_relativo_min:Q', title='Tiempo relativo a salida (min)'),
        y=alt.Y('SOG:Q', title='SOG (knots)'),
        color=alt.Color('Track:N', scale=color_scale, legend=alt.Legend(title="Track", orient='top'))
    ).properties(width=900, height=250)

    # --- Combinar ---
    st.altair_chart(chart_sog, use_container_width=True)

# Arma los datos para la tabla resumen
sog_data = {}
track_labels = [f"{track1} (azul)", f"{track2} (naranja)"]
track_dfs = [df1_plot, df2_plot]

for track_label, track_df in zip(track_labels, track_dfs):
    if not track_df.empty and not track_df['SOG'].isnull().all():
        idx_max_sog = track_df['SOG'].idxmax()
        idx_min_sog = track_df['SOG'].idxmin()
        sog_max = f"{track_df['SOG'].max():.2f} ({track_df.loc[idx_max_sog, 'TWA']:.1f}°)"
        sog_min = f"{track_df['SOG'].min():.2f} ({track_df.loc[idx_min_sog, 'TWA']:.1f}°)"
        sog_avg = f"{track_df['SOG'].mean():.2f} ({mean_circ_signed_deg(track_df['TWA']):.1f}°)"
    else:
        sog_max = sog_min = sog_avg = "-"
    sog_data[track_label] = [sog_max, sog_min, sog_avg]

tabla_sog = pd.DataFrame(
    sog_data,
    index=["SOG máximo knots (TWA)", "SOG mínimo knots (TWA)", "SOG promedio knots (TWA medio)"]
)

st.dataframe(tabla_sog, use_container_width=True)

# === Rosa de COG (frecuencia) – 10° por sector, colores de tracks ===
import matplotlib.pyplot as plt

st.subheader("🌬️ Rosa de COG – Frecuencia (10°)")
st.markdown("""
La dirección de la barra representa el rumbo (COG) del barco y la longitud representa el % del tiempo estuvo navegando en ese rumbo.
""")

# Bins: 36 sectores de 10°
edges_deg = np.arange(0, 361, 10)            # [0, 10, 20, ..., 360]
sector_labels = [f"{int(x)}" for x in edges_deg[:-1]]
width = np.deg2rad(10)                       # ancho de cada barra

def _rose_freq(df_src, titulo="Rosa COG", facecolor="#999999", edgecolor="black", alpha=0.85):
    fig = plt.figure(figsize=(3, 3))
    ax = plt.subplot(111, polar=True)

    if df_src is None or df_src.empty or "COG" not in df_src.columns:
        ax.set_axis_off()
        ax.set_title(f"{titulo}\n(sin datos)")
        return fig

    # Normaliza a [0, 360) y discretiza en sectores de 10°
    cog_norm = (pd.to_numeric(df_src["COG"], errors="coerce") % 360).dropna().astype(float)
    sectors = pd.cut(cog_norm, bins=edges_deg, right=False, labels=sector_labels, include_lowest=True)

    # Conteo y frecuencia
    counts = sectors.value_counts().sort_index()
    freq = counts / counts.sum() if counts.sum() > 0 else counts

    # Ángulo de inicio de cada sector (0°, 10°, 20°...). Si prefieres centrar, suma 5° antes de pasar a radianes.
    angles = np.deg2rad(freq.index.astype(float).values) if len(freq) else np.array([])

    # Dibujo
    if len(freq):
        ax.bar(
            angles,
            freq.values,
            width=width,
            edgecolor=edgecolor,
            color=facecolor,
            alpha=alpha,
        )

    # Convención náutica: norte arriba, sentido horario
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)

    # Etiquetas radiales y título
    ax.set_rlabel_position(225)
    ax.set_title(titulo)

    ax.set_yticks([0.05, 0.10, 0.15, 0.20])
    ax.set_yticklabels(['5%', '10%', '15%', '20%'])


    return fig

col1, col2 = st.columns(2)

# Track 1 (azul)
with col1:
    if 'df1_plot' in locals() and df1_plot is not None and not df1_plot.empty:
        fig1 = _rose_freq(
            df1_plot,
            titulo=f"Rosa COG – {track1} (azul)",
            facecolor="#0064FF",   # color de relleno track 1
            edgecolor="#0064FF"    # borde a juego
        )
        st.pyplot(fig1, use_container_width=False)
    else:
        st.info("Selecciona un Track 1 para ver su rosa de COG.")

# Track 2 (naranja)
with col2:
    if 'df2_plot' in locals() and df2_plot is not None and not df2_plot.empty:
        fig2 = _rose_freq(
            df2_plot,
            titulo=f"Rosa COG – {track2} (naranja)",
            facecolor="#FF6400",   # color de relleno track 2
            edgecolor="#FF6400"    # borde a juego
        )
        st.pyplot(fig2, use_container_width=False)
    else:
        st.info("Selecciona un Track 2 para ver su rosa de COG.")

# --- TABLA RESUMEN DE COG ---
cog_data = {}

for track_label, track_df in zip(track_labels, track_dfs):

    # --- valores por defecto SIEMPRE ---
    m1 = m2 = m3 = m4 = diff = cog_std = "-"
    if not track_df.empty and "COG" in track_df and not track_df["COG"].isnull().all():

        modes = circular_modes_deg(track_df["COG"], bin_size=10, top_n=4)

        if len(modes) >= 1:
            m1 = f"{modes[0][0]:.0f}° ({modes[0][1]:.0f}%)"
        if len(modes) >= 2:
            m2 = f"{modes[1][0]:.0f}° ({modes[1][1]:.0f}%)"
            diff_val = abs((modes[0][0] - modes[1][0] + 180) % 360 - 180)
            diff = f"{diff_val:.0f}°"
        if len(modes) >= 3:
            m3 = f"{modes[2][0]:.0f}° ({modes[2][1]:.0f}%)"
        if len(modes) >= 4:
            m4 = f"{modes[3][0]:.0f}° ({modes[3][1]:.0f}%)"

        cog_std = f"{circstd(track_df['COG'].dropna(), high=360, low=0):.1f}"

    cog_data[track_label] = [m1, m2, m3, m4, diff, cog_std]

tabla_cog = pd.DataFrame(
    cog_data,
    index=[
        "COG dominante 1",
        "COG dominante 2",
        "COG dominante 3",
        "COG dominante 4",
        "Separación angular",
        "Dispersión (std)*",
    ],
)

st.dataframe(tabla_cog, use_container_width=True)


st.caption(
        "*Si es baja → el barco mantuvo rumbo muy estable. Si es alta → hubo cambios de rumbo (maniobras, zigzags, etc)."
    )

# --- EVOLUCIÓN DE SOG y COG ---
st.subheader("📈 Evolución de SOGS y COG (superpuesto)")
def plot_sog_cog_superpuesto(df, track_color, track_label):
    if df.empty:
        return None

    base = alt.Chart(df).encode(
        x=alt.X('UTC:T', title='Hora GPS'),
        #x=alt.X('Tiempo_relativo_min:Q', title='Tiempo relativo a salida (min)'),
    )
    sog_line = base.mark_line(
        color=track_color,
        strokeWidth=2,
        opacity=1.0
    ).encode(
        y=alt.Y(
            'SOGS:Q',
            title='SOGS (knots)'
            # Opcional: axis=alt.Axis(values=[...]) si quieres ticks específicos
        )
    )

    cog_line = base.mark_line(
        color='#333333',
        strokeWidth=1.2,
        opacity=1.0
    ).encode(
        y=alt.Y(
            'COG:Q',
            title='COG (°)',
            scale=alt.Scale(domain=[0, 360]),
            axis=alt.Axis(
                values=list(range(0, 361, 30)),  # 0,30,60,...,360
                tickCount=13
            )
        )
    )

    chart = alt.layer(
        sog_line,
        cog_line
    ).resolve_scale(
        y='independent'   # mantiene escalas independientes para SOG y COG
    ).properties(
        width=900, height=250,  
        title=f"SOGS (color) y COG (gris) - {track_label}"
    )

    return chart

# Para el track azul
if not df1_plot.empty:
    chart_azul = plot_sog_cog_superpuesto(df1_plot, '#0064FF', f"{track1} (azul)")
    st.altair_chart(chart_azul, use_container_width=True)

# Para el track naranja
if not df2_plot.empty:
    chart_naranja = plot_sog_cog_superpuesto(df2_plot, '#FF6400', f"{track2} (naranja)")
    st.altair_chart(chart_naranja, use_container_width=True)

# --- HISTOGRAMA DE SOG (agrupado si hay dos tracks) ---
bin_size = 0.5  # ancho de bin en nudos (ajústalo si quieres)
df_hist = []

for track_label, track_df in zip(track_labels, track_dfs):
    if track_df.empty or 'SOG' not in track_df.columns:
        continue

    sog_vals = track_df['SOG'].dropna()
    if sog_vals.empty:
        continue

    bins = np.arange(
        sog_vals.min(),
        sog_vals.max() + bin_size,
        bin_size
    )

    hist, edges = np.histogram(sog_vals, bins=bins)
    total = hist.sum()
    if total == 0:
        continue

    for i, count in enumerate(hist):
        if count == 0:
            continue
        df_hist.append({
            "SOG_bin": (edges[i] + edges[i + 1]) / 2,
            "Porcentaje": 100 * count / total,
            "Track": track_label
        })

df_hist = pd.DataFrame(df_hist)

st.subheader("📊 Histograma de SOG (knots) normalizado (%)")

hist_sog = (alt.Chart(df_hist).mark_bar(size=30, opacity=0.7).encode(
        x=alt.X(
            'SOG_bin:Q',
            title='SOG (knots)',
            bin=alt.Bin(step=bin_size)
        ),
        y=alt.Y(
            'Porcentaje:Q',
            title='Porcentaje (%)',
            stack=None
        ),
        color=alt.Color(
            'Track:N',
            scale=color_scale,
            legend=alt.Legend(title="Track", orient='top')
        ),
        xOffset='Track:N',   # esto evita el apilado
        tooltip=[
            alt.Tooltip('Track:N'),
            alt.Tooltip('Porcentaje:Q', format=".1f")
        ]
    )
    .properties(width=900, height=250)
)

st.altair_chart(hist_sog, use_container_width=True)
st.caption(
        "Histograma normalizado: cada barra representa el porcentaje de tiempo "
        "en cada rango de velocidad, independiente de la frecuencia de muestreo."
    )

# --- TABLA RESUMEN SOG ---
sog_data = {}
sog_avgs = {}  # para calcular Δ SOG entre tracks

for label, df in zip(track_labels, track_dfs):
    if not df.empty and "SOG" in df and not df["SOG"].isna().all():

        # Modos de SOG
        modes = sog_modes(df, bin_width=0.5, top_n=2)

        if len(modes) >= 1:
            m1 = f"{modes[0][0]:.1f} kn ({modes[0][1]:.0f}%)"
        else:
            m1 = "-"

        if len(modes) >= 2:
            m2 = f"{modes[1][0]:.1f} kn ({modes[1][1]:.0f}%)"
        else:
            m2 = "-"

        avg_val = df["SOG"].mean()
        avg = f"{avg_val:.2f}"
        std = f"{df['SOG'].std():.2f}"

        sog_avgs[label] = avg_val

    else:
        m1 = m2 = avg = std = "-"
        sog_avgs[label] = None

    sog_data[label] = [m1, m2, avg, std]

# --- Δ SOG ENTRE TRACKS ---
delta_row = {}

if len(track_labels) == 2:
    l1, l2 = track_labels
    a1, a2 = sog_avgs[l1], sog_avgs[l2]

    if a1 is not None and a2 is not None:
        delta = a1 - a2
        delta_row[l1] = f"{delta:+.2f} kn"
        delta_row[l2] = f"{-delta:+.2f} kn"
    else:
        delta_row[l1] = delta_row[l2] = "-"
else:
    # Solo un track → no aplica
    for l in track_labels:
        delta_row[l] = "-"

# --- Construir DataFrame final ---
tabla_sog = pd.DataFrame(
    sog_data,
    index=[
        "SOG dominante",
        "SOG dominante 2",
        "SOG promedio",
        "Dispersión (std)",
    ],
)

tabla_sog.loc["Δ SOG vs otro barco"] = delta_row

st.dataframe(tabla_sog, use_container_width=True)

st.caption(
    "Δ SOG: diferencia de velocidad media respecto al otro barco. "
    "Valor positivo = más rápido."
)

# --- EVOLUCIÓN DE SOGS suavizado / smooth ---
st.subheader("📈 Evolución de SOGS suavizado (knots)")
if not df_plot.empty:
    # --- Línea vertical en minuto de salida ---
    linea_salida = alt.Chart(pd.DataFrame({'Tiempo_relativo_min': [0]})).mark_rule(
        color='black',
        strokeDash=[4, 4],
        size=2
    ).encode(
        x='Tiempo_relativo_min:Q'
    )

    # --- Gráfico de SOG ---
    chart_sog = alt.Chart(df_plot).mark_line(opacity=0.9).encode(
        x=alt.X('UTC:T', title='Hora GPS'),
        #x=alt.X('Tiempo_relativo_min:Q', title='Tiempo relativo a salida (min)'),
        y=alt.Y('SOGS:Q', title='SOGS (knots)'),
        color=alt.Color('Track:N', scale=color_scale, legend=alt.Legend(title="Track", orient='top'))
    ).properties(width=900, height=250)

    # --- Combinar ---
    st.altair_chart(chart_sog, use_container_width=True)

# Arma los datos para la tabla resumen
sog_data = {}
track_labels = [f"{track1} (azul)", f"{track2} (naranja)"]
track_dfs = [df1_plot, df2_plot]

for track_label, track_df in zip(track_labels, track_dfs):
    if not track_df.empty and not track_df['SOGS'].isnull().all():
        idx_max_sog = track_df['SOGS'].idxmax()
        idx_min_sog = track_df['SOGS'].idxmin()
        sog_max = f"{track_df['SOGS'].max():.2f} ({track_df.loc[idx_max_sog, 'TWA']:.1f}°)"
        sog_min = f"{track_df['SOGS'].min():.2f} ({track_df.loc[idx_min_sog, 'TWA']:.1f}°)"
        sog_avg = f"{track_df['SOGS'].mean():.2f} ({mean_circ_signed_deg(track_df['TWA']):.1f}°)"
    else:
        sog_max = sog_min = sog_avg = "-"
    sog_data[track_label] = [sog_max, sog_min, sog_avg]

tabla_sog = pd.DataFrame(
    sog_data,
    index=["SOGS máximo knots (TWA)", "SOGS mínimo knots (TWA)", "SOGS promedio knots (TWA medio)"]
)

st.dataframe(tabla_sog, use_container_width=True)

# --- EVOLUCIÓN DE VMG ---
st.subheader("📈 Evolución de VMG (knots)")
if not df_plot.empty and 'VMG' in df_plot.columns:
    chart_vmg = alt.Chart(df_plot).mark_line(opacity=0.9).encode(
        x=alt.X('UTC:T', title='Hora GPS'),
        #x=alt.X('Tiempo_relativo_min:Q', title='Tiempo relativo a salida (min)'),
        y=alt.Y('VMG:Q', title='VMG (knots)'),
        color=alt.Color('Track:N', scale=color_scale, legend=alt.Legend(title="Track", orient='top'))
    ).properties(width=900, height=250)
    st.altair_chart(chart_vmg, use_container_width=True)

sel_tramo = "indefinido"
if sel_tramo == "Ceñida":
    st.caption("🔵 *En ceñida* el objetivo es que el VMG sea lo más alto posible (positivo). El valor destacado indica el mejor rendimiento hacia barlovento en el tramo.")
elif sel_tramo == "Popa":
    st.caption("🟠 *En popa* el objetivo es que el VMG sea lo más bajo posible (negativo). El valor destacado indica el mejor rendimiento hacia sotavento en el tramo.")
else:
    st.caption(
        "En ceñida (hacia barlovento) es mejor un VMG positivo alto. En popa (hacia sotavento) es mejor un VMG negativo más bajo (más negativo). "
    )

# Arma los datos para la tabla resuen
vmg_data = {}
track_labels = [f"{track1} (azul)", f"{track2} (naranja)"]
track_dfs = [df1_plot, df2_plot]

for track_label, track_df in zip(track_labels, track_dfs):
    if not track_df.empty and not track_df['VMG'].isnull().all():
        idx_max_vmg = track_df['VMG'].idxmax()
        idx_min_vmg = track_df['VMG'].idxmin()
        vmg_max = f"{track_df['VMG'].max():.2f} ({track_df.loc[idx_max_vmg, 'TWA']:.1f}°)"
        vmg_min = f"{track_df['VMG'].min():.2f} ({track_df.loc[idx_min_vmg, 'TWA']:.1f}°)"
        vmg_avg = f"{track_df['VMG'].mean():.2f} ({mean_circ_signed_deg(track_df['TWA']):.1f}°)"
    else:
        vmg_max = vmg_min = vmg_avg = "-"
    vmg_data[track_label] = [vmg_max, vmg_min, vmg_avg]

# Construye el DataFrame resumen
tabla_vmg = pd.DataFrame(
    vmg_data,
    index=["VMG máximo knots, (TWA)", "VMG mínimo knots (TWA)", "VMG promedio knots (TWA medio)"]
)
st.dataframe(tabla_vmg, use_container_width=True)
# --- FIN EVOLUCIÓN DE VMG ---

# --- EVOLUCIÓN DE TWA ----
st.subheader("📈 Evolución de TWA_abs (°)")
if not df_plot.empty and 'TWA' in df_plot.columns:
    chart_twa = alt.Chart(df_plot).mark_line(opacity=0.9).encode(
        x=alt.X('UTC:T', title='Hora GPS'),
        #x=alt.X('Tiempo_relativo_min:Q', title='Tiempo relativo a salida (min)'),
        y=alt.Y(
            'TWA_abs:Q',
            title='TWA_abs (°)',
            scale=alt.Scale(domain=[0, 180]),
            axis=alt.Axis(values=list(range(0, 181, 30)))
        ),
        color=alt.Color('Track:N', scale=color_scale, legend=alt.Legend(title="Track", orient='top'))
    ).properties(width=900, height=300)
    st.altair_chart(chart_twa, use_container_width=True)
    st.caption("negativo amurado a estribor y positivo amurado a babor")
# --- FIN EVOLUCIÓN DE TWA ---

# --- DISPERSIÓN SOG vs TWA ---
st.subheader("📊 SOG vs. TWA (dispersión)")
if not df_plot.empty:
    scatter_sog_twa = alt.Chart(df_plot).mark_circle(size=45, opacity=0.6).encode(
        x=alt.X(
            'TWA:Q',
            title='TWA (°)',
            scale=alt.Scale(domain=[-180, 180]),
            axis=alt.Axis(values=list(range(-180, 181, 10)))
        ),
        y=alt.Y('SOG:Q', title='SOG (knots)'),
        color=alt.Color('Track:N', scale=color_scale,
                        legend=alt.Legend(title="Track", orient='top')),
        tooltip=['UTC:T', 'SOG:Q', 'TWA:Q', 'Track:N']
    ).properties(width=900, height=300)

    st.altair_chart(scatter_sog_twa, use_container_width=True)
# --- FIN DISPERSIÓN SOG vs TWA ---

# --- DISPERSIÓN VMG vs TWA ---
st.subheader("📊 VMG vs. TWA (dispersión)")
st.markdown("""
**Este gráfico muestra cómo varía el _VMG_ (Velocity Made Good) según el _TWA_ (ángulo real al viento):**
- Cada punto representa un registro individual del track.
- Permite ver a qué ángulos al viento el barco obtiene el mejor o peor VMG.
- **En ceñida** (TWA bajo, cerca de 45°): buscá puntos con VMG positivo alto.
- **En popa** (TWA alto, cerca de 150°-180°): el mejor VMG es el valor más negativo.
- La nube de puntos ayuda a identificar las “zonas óptimas” para navegar según las condiciones del tramo.
""")
if not df_plot.empty and 'VMG' in df_plot.columns and 'TWA' in df_plot.columns:
    scatter_vmg_twa = alt.Chart(df_plot).mark_circle(size=45, opacity=0.6).encode(
        x=alt.X(
            'TWA:Q',
            title='TWA (°)',
            scale=alt.Scale(domain=[-180, 180]),
            axis=alt.Axis(values=list(range(-180, 181, 10)))
        ),
        y=alt.Y('VMG:Q', title='VMG (knots)'),
        color=alt.Color('Track:N', scale=color_scale,
                        legend=alt.Legend(title="Track", orient='top')),
        tooltip=['UTC:T', 'VMG:Q', 'TWA:Q', 'Track:N']
    ).properties(width=900, height=300)

    st.altair_chart(scatter_vmg_twa, use_container_width=True)
   
# --- ANÁLISIS DE MANIOBRAS Y BASADA EN COG ---
st.subheader("🔄 Análisis de maniobras basado en COG")

# Ajustes de usuario para detección de maniobras (puedes mover a sidebar)
umbral_maniobra = st.number_input(
    "Umbral de detección de maniobra (° cambio de COG vs. mediana de ventana)", 
    min_value=10, max_value=180, value=30, step=5,
    help="Valor mínimo de cambio de rumbo (COG) para considerar que hay una maniobra. Un valor más bajo detecta más maniobras (incluyendo pequeños zigzags); un valor más alto solo detecta cambios de rumbo grandes."
)
window = st.number_input(
    "Tamaño de la ventana deslizante (n° de puntos)",
    min_value=3, max_value=20, value=10, step=1,
    help="Cantidad de puntos para calcular la media previa y posterior"
)
tiempo_minimo = st.number_input(
    "Tiempo mínimo entre maniobras detectadas (segundos)",
    min_value=5, max_value=60, value=18, step=1,
    help="Descarta maniobras consecutivas muy cercanas en el tiempo"
)

def circ_diff_deg(a, b):
    """Diferencia angular mínima en grados (resultado en [-180, +180])."""
    return (a - b + 180) % 360 - 180

# --- Detección de maniobras (con COG circular) ---
maniobra_points = []
if not df_plot.empty:
    for track in df_plot['Track'].unique():
        track_df = (
            df_plot[df_plot['Track'] == track]
            .sort_values('UTC')
            .reset_index(drop=True)
        )

        # Asegura dominio [0,360) para cálculos circulares
        cogs = np.mod(track_df['COG'].values, 360.0)
        times = track_df['UTC'].values

        for i in range(window, len(cogs) - window):
            ventana_prev = cogs[i - window : i]
            ventana_post = cogs[i + 1 : i + 1 + window]

            # Medias CIRCULARES de ventanas
            media_prev = float(circmean(ventana_prev, high=360, low=0))
            media_post = float(circmean(ventana_post, high=360, low=0))

            # Diferencias CIRCULARES con el punto actual
            diff_prev = abs(circ_diff_deg(cogs[i], media_prev))
            diff_post = abs(circ_diff_deg(cogs[i], media_post))

            # Usa la mayor (o podrías usar el promedio) como “intensidad” de maniobra
            diff = max(diff_prev, diff_post)

            if diff > umbral_maniobra:
                maniobra_points.append({
                    "UTC": times[i],
                    "COG": cogs[i],
                    "COG_previo": media_prev,
                    "COG_post": media_post,
                    "Track": track,
                    "idx": i,
                })
maniobra_df = pd.DataFrame(maniobra_points)

# --- Sincronizar maniobra_df con tiempo relativo ---
if not maniobra_df.empty:
    maniobra_df = maniobra_df.merge(
        df_plot[['UTC', 'Track', 'Tiempo_relativo_min']],
        on=['UTC', 'Track'],
        how='left'
    )

# --- Filtro: eliminar maniobras muy cercanas en el tiempo ---
if not maniobra_df.empty:
    maniobra_df = maniobra_df.sort_values(['Track', 'UTC']).reset_index(drop=True)
    maniobra_df["keep"] = True
    for track in maniobra_df['Track'].unique():
        track_df_m = maniobra_df[maniobra_df["Track"] == track]
        last_time = None
        for i, row in track_df_m.iterrows():
            if last_time is not None and (row["UTC"] - last_time).total_seconds() < tiempo_minimo:
                maniobra_df.at[i, "keep"] = False
            else:
                last_time = row["UTC"]
    maniobra_df = maniobra_df[maniobra_df["keep"]].reset_index(drop=True)

# --- VISUALIZACIÓN DEL GRÁFICO ---
chart_cog = alt.Chart(df_plot).mark_line(opacity=1).encode(
    x=alt.X('UTC:T', title='Hora GPS'),
    #x=alt.X('Tiempo_relativo_min:Q', title='Tiempo relativo a salida (min)'),
    y=alt.Y(
        'COG:Q',
        title='COG (°)',
        scale=alt.Scale(domain=[0, 360]),
        axis=alt.Axis(
            values=list(range(0, 361, 30)),
            tickCount=13
        )
    ),
    color=alt.Color('Track:N', scale=color_scale, legend=alt.Legend(title="Track", orient='top'))
)
if not maniobra_df.empty:
    points = alt.Chart(maniobra_df).mark_point(
        shape='diamond',
        size=150,
        filled=True,
        stroke='black',
        strokeWidth=3
    ).encode(
        color=alt.Color('Track:N', scale=color_scale, legend=None)
    ).encode(
        x='UTC:T',
        y='COG:Q',
        tooltip=['UTC:T', 'COG:Q', 'Track:N']
    )
    chart_final = chart_cog + points
    st.altair_chart(chart_final.properties(width=900, height=300), use_container_width=True)
    # Resumen de maniobras por track
    conteo_tracks = maniobra_df.groupby("Track").size().to_dict()
    resumen_txt = ", ".join([f"{track}: {count}" for track, count in conteo_tracks.items()])
    #st.caption(f"Se detectaron **{len(maniobra_df)}** maniobras únicas. Desglose por track: {resumen_txt}")

    tabla_maniobras = pd.DataFrame(
        [conteo_tracks],
        index=["Maniobras detectadas"]
    )
    st.dataframe(tabla_maniobras, use_container_width=False)

# --- TABLA DETALLADA DE VELOCIDAD ANTES Y DESPUÉS DE CADA MANIOBRA (con COG previo y post) ---

if maniobra_df.empty:
    st.caption("No se detectaron maniobras para este tramo/umbral.")
else:
    ventana_input = st.text_input(
        "Ventanas de tiempo (segundos, negativos para antes y positivos para después, separados por coma)",
        value="-8,-5,-3,-2,-1,0,1,2,3,5,8,12"
    )
    try:
        ventanas = [int(s) for s in ventana_input.replace(' ', '').split(',') if s]
        ventanas = sorted(set(ventanas))
    except Exception as e:
        st.error(f"Error en las ventanas: {e}")
        ventanas = [0]
    ventana_labels = [f"{n:+d}s" if n != 0 else "0s" for n in ventanas]

    tabla = []
    t_prev = 8   # segundos antes de la maniobra para calcular SOG previa
    t_post_max = 30  # segundos después para buscar la recuperación

    for idx, maniobra in maniobra_df.iterrows():
        track = maniobra["Track"]
        time = maniobra["UTC"]
        df_este_track = df_plot[df_plot["Track"] == track]
        delta_cog = ((maniobra["COG_post"] - maniobra["COG_previo"] + 180) % 360) - 180
        delta_cog = round(delta_cog, 0)

        # SOG previa a la maniobra
        rango_previo = (time - pd.Timedelta(seconds=t_prev), time)
        sog_previa = df_este_track[
            (df_este_track["UTC"] >= rango_previo[0]) & (df_este_track["UTC"] <= rango_previo[1])
        ]["SOG"].mean()

        # Tiempo hasta recuperar SOG previa después de la maniobra
        tiempo_recuperacion = None
        for t in range(1, t_post_max + 1):
            instante = time + pd.Timedelta(seconds=t)
            sog_inst = df_este_track[
                (df_este_track["UTC"] >= instante - pd.Timedelta(seconds=0.5)) &
                (df_este_track["UTC"] <= instante + pd.Timedelta(seconds=0.5))
            ]["SOG"].mean()
            if not np.isnan(sog_inst) and sog_inst >= sog_previa:
                tiempo_recuperacion = t
                break
        if tiempo_recuperacion is None:
            tiempo_recuperacion = t_post_max + 1  # o "No recuperada" si prefieres

        fila = {
            "Track": track,
            "Momento": time.strftime("%H:%M:%S"),
            #"COG previo": round(maniobra["COG_previo"], 0),
            #"COG post": round(maniobra["COG_post"], 0),
            #"Delta COG": delta_cog,
            "SOG previa": f"{sog_previa:.2f}" if not np.isnan(sog_previa) else "-",
            "Recup. SOG (s)": tiempo_recuperacion if tiempo_recuperacion <= t_post_max else "+30",
        }
        for delta, label in zip(ventanas, ventana_labels):
            if delta == 0:
                rango = (time - pd.Timedelta(seconds=0.5), time + pd.Timedelta(seconds=0.5))
            elif delta < 0:
                rango = (time + pd.Timedelta(seconds=delta), time)
            else:
                rango = (time, time + pd.Timedelta(seconds=delta))
            tramo = df_este_track[
                (df_este_track["UTC"] >= rango[0]) & (df_este_track["UTC"] <= rango[1])
            ]
            vel_media = tramo["SOG"].mean()
            fila[label] = f"{vel_media:.2f}" if not np.isnan(vel_media) else "-"
        tabla.append(fila)

    columnas_finales = [
        "Track", 
        "Momento", 
        #"COG previo", 
        #"COG post", 
        #"Delta COG",
        "SOG previa", 
        "Recup. SOG (s)"
    ] + ventana_labels

    tabla_df = pd.DataFrame(tabla)
    tabla_df = tabla_df[columnas_finales]

    # Resaltado visual: rápido (verde), lento/no (rojo)
    def highlight_recup(val):
        try:
            if val == "No recuperada":
                return "background-color: #FFCCCC; color: #990000"
            v = int(val)
            if v <= 5:
                return "background-color: #C7FFCD; color: #005900"  # verde
            elif v <= 15:
                return "background-color: #FFFFD1; color: #C0A000"  # amarillo
            else:
                return "background-color: #FFCCCC; color: #990000"  # rojo
        except:
            return ""

    # velocidad maniobra, recuperación
    st.markdown("#### Tabla: velocidad media antes y después de cada maniobra y tiempo hasta recuperar SOG previa")

    # Convertir a string para evitar error con Arrow
    tabla_df["Recup. SOG (s)"] = tabla_df["Recup. SOG (s)"].astype(str)

    st.dataframe(
        tabla_df.style.map(highlight_recup, subset=["Recup. SOG (s)"]),
        hide_index=False,
        use_container_width=True
    )

## ANALISIS DE TRAMOS
def tramo_tipo_twa(twa_mean):
    if np.isnan(twa_mean):
        return "None"
    abs_twa = abs(twa_mean)
    if abs_twa < 70:
        return "ceñida"
    elif abs_twa > 135:
        return "popa"
    else:
        return "través"


if not maniobra_df.empty:
    st.markdown("#### Análisis de tramos entre maniobras (SOG, COG y TWA)")
    tramo_rows = []
    for track in maniobra_df["Track"].unique():
        df_track = df_plot[df_plot["Track"] == track].reset_index(drop=True)
        maniobras_idx = maniobra_df[maniobra_df["Track"] == track]["idx"].tolist()
        if 0 not in maniobras_idx:
            maniobras_idx = [0] + maniobras_idx
        if (len(df_track) - 1) not in maniobras_idx:
            maniobras_idx.append(len(df_track) - 1)
        maniobras_idx = sorted(set(maniobras_idx))
        for j in range(len(maniobras_idx) - 1):
            ini = maniobras_idx[j]
            fin = maniobras_idx[j + 1]
            tramo = df_track.iloc[ini:fin + 1]
            if tramo.empty:
                continue
            sog_mean = tramo["SOG"].mean()
            cog_mean = tramo["COG"].mean()
            cog_mean = circmean(tramo["COG"].dropna(), high=360, low=0)
            cog_std = circstd(tramo["COG"].dropna(), high=360, low=0)
            twa_mean = mean_circ_signed_deg(tramo["TWA_abs"]) if "TWA_abs" in tramo else np.nan
            tramo_tipo = tramo_tipo_twa(twa_mean)
            utc_ini = tramo["UTC"].iloc[0]
            utc_fin = tramo["UTC"].iloc[-1]
            duracion = (pd.to_datetime(utc_fin) - pd.to_datetime(utc_ini)).total_seconds()
            # Duración en mm:ss
            minutos = int(duracion // 60)
            segundos = int(duracion % 60)
            duracion_str = f"{minutos:02}:{segundos:02}"
            hora_ini = pd.to_datetime(utc_ini).strftime("%H:%M:%S")
            hora_fin = pd.to_datetime(utc_fin).strftime("%H:%M:%S")
            tramo_rows.append({
                "Track": track,
                "Duración": duracion_str,
                "SOG prom.": f"{sog_mean:.2f}",
                "COG prom.": f"{cog_mean:.1f}",
                "Desvío COG": f"{cog_std:.1f}",
                "TWA prom.": f"{twa_mean:.1f}" if not np.isnan(twa_mean) else "-",
                "Tramo": tramo_tipo,
                "Hora inicio": hora_ini,
                "Hora fin": hora_fin,
            })
    if tramo_rows:
        tabla_tramos = pd.DataFrame(tramo_rows)
        st.dataframe(tabla_tramos, hide_index=False, use_container_width=True)
        st.caption("""
            **Desvío COG** indica la variabilidad del rumbo (COG) durante el tramo. Un valor bajo significa que el barco mantuvo un rumbo muy estable; un valor alto indica cambios frecuentes de rumbo, zigzags o maniobras.
            """)
    else:
        st.info("No hay tramos entre maniobras detectados.")

# --- ANALISIS Y TABLAS BASADAS EN VMG ---

# RANKING POR TRAMO

st.subheader("🏅 Ranking por tramo: VMG en ceñida y popa")

ranking_vmg = []
for i, df in enumerate(track_dfs):
    if df.empty:
        ranking_vmg.append({
            "Track": track_labels[i],
            "VMG Ceñida (prom)": "-",
            "VMG Popa (prom)": "-"
        })
        continue

    # Ceñida: TWA entre 40° y 70°
    ceñida = df[(df["TWA"].abs() >= 40) & (df["TWA"].abs() <= 70)]
    vmg_cejida_prom = ceñida["VMG"].mean() if not ceñida.empty else float('nan')

    # Popa: TWA >= 135°
    popa = df[df["TWA"].abs() >= 135]
    vmg_popa_prom = popa["VMG"].mean() if not popa.empty else float('nan')

    ranking_vmg.append({
        "Track": track_labels[i],
        "VMG Ceñida (prom)": f"{vmg_cejida_prom:.2f}" if not np.isnan(vmg_cejida_prom) else "-",
        "VMG Popa (prom)": f"{vmg_popa_prom:.2f}" if not np.isnan(vmg_popa_prom) else "-"
    })

ranking_df = pd.DataFrame(ranking_vmg)
st.dataframe(ranking_df, use_container_width=True)


# MEJOR Y PEOR TRAMO

# Tamaño de la ventana (en puntos consecutivos)
window = 20  # Tamaño de la ventana (en puntos consecutivos)
window = st.number_input(
    "Tamaño de la ventana deslizante (n° de puntos)",
    min_value=10, max_value=120, value=20, step=5,
    help="Cantidad de puntos para calcular mejor/peor ceñida y popa"
)

# -------- Mejor ceñida / popa --------
st.subheader("⛵ Mejor tramo de ceñida / popa de cada track")
mejor_tramos = []

for i, df in enumerate(track_dfs):
    if df.empty:
        for tramo, rango, label in [
            ("ceñida", (40, 70), "ceñida"),
            ("popa", (135, 180), "popa")
            #("través",(71,134),"través")
        ]:
            mejor_tramos.append({
                "Track": track_labels[i], 
                "Tipo": label,
                "TWA inicio": "-", 
                "TWA fin": "-", 
                "UTC inicio": "-", 
                "UTC fin": "-",
                "VMG promedio": "-", 
                "Duración (s)": "-", 
                "Distancia (m)": "-"
            })
        continue

    for tramo, rango, label in [
        ("ceñida", (40, 70), "ceñida"),
        ("popa", (135, 180), "popa")
        #("través",(71,134),"través")
    ]:
        df_rango = df[(df["TWA"].abs() >= rango[0]) & (df["TWA"].abs() <= rango[1])].reset_index(drop=True)
        if len(df_rango) < window:
            mejor_tramos.append({
                "Track": track_labels[i], 
                "Tipo": label,
                "TWA inicio": "-", 
                "TWA fin": "-", 
                "UTC inicio": "-", 
                "UTC fin": "-",
                "VMG promedio": "-", 
                "Duración (s)": "-", 
                "Distancia (m)": "-"
            })
            continue

        idx_best = -1
        if label == "ceñida":
            # Ceñida: buscar máximo VMG promedio (más positivo)
            best_vmg = float('-inf')
            for idx in range(len(df_rango) - window + 1):
                vmg_prom = df_rango.loc[idx:idx+window-1, "VMG"].mean()
                if vmg_prom > best_vmg:
                    best_vmg = vmg_prom
                    idx_best = idx
            vmg_val = best_vmg
        else:
            # Popa: buscar mínimo VMG promedio (más negativo)
            best_vmg = float('inf')
            for idx in range(len(df_rango) - window + 1):
                vmg_prom = df_rango.loc[idx:idx+window-1, "VMG"].mean()
                if vmg_prom < best_vmg:
                    best_vmg = vmg_prom
                    idx_best = idx
            vmg_val = best_vmg

        tramo_best = df_rango.loc[idx_best:idx_best+window-1]
        utc_ini = tramo_best["UTC"].iloc[0]
        utc_fin = tramo_best["UTC"].iloc[-1]
        twa_ini = tramo_best["TWA"].iloc[0]
        twa_fin = tramo_best["TWA"].iloc[-1]
        duracion = (pd.to_datetime(utc_fin) - pd.to_datetime(utc_ini)).total_seconds()
        distancia = tramo_best["Dist"].sum()

        mejor_tramos.append({
            "Track": track_labels[i], 
            "Tipo": label,
            "TWA inicio": f"{twa_ini:.1f}", 
            "TWA fin": f"{twa_fin:.1f}",
            "UTC inicio": pd.to_datetime(utc_ini).strftime("%H:%M:%S"),
            "UTC fin": pd.to_datetime(utc_fin).strftime("%H:%M:%S"),
            "VMG promedio": f"{vmg_val:.2f}",
            "Duración (s)": f"{duracion:.1f}", 
            "Distancia (m)": f"{distancia:.1f}"
        })

mejor_tramos_df = pd.DataFrame(mejor_tramos)
st.dataframe(mejor_tramos_df, use_container_width=True)

# -------- Peor ceñida / popa --------
st.subheader("⛵ Peor tramo de ceñida / popa de cada track")
peor_tramos = []

for i, df in enumerate(track_dfs):
    if df.empty:
        for tramo, rango, label in [
            ("ceñida", (40, 70), "ceñida"),
            ("popa", (135, 180), "popa")
        ]:
            peor_tramos.append({
                "Track": track_labels[i], 
                "Tipo": label,
                "TWA inicio": "-", 
                "TWA fin": "-", 
                "UTC inicio": "-", 
                "UTC fin": "-",
                "VMG promedio": "-", 
                "Duración (s)": "-", 
                "Distancia (m)": "-"
            })
        continue

    for tramo, rango, label in [
        ("ceñida", (40, 70), "ceñida"),
        ("popa", (135, 180), "popa")
    ]:
        df_rango = df[(df["TWA"].abs() >= rango[0]) & (df["TWA"].abs() <= rango[1])].reset_index(drop=True)
        if len(df_rango) < window:
            peor_tramos.append({
                "Track": track_labels[i], 
                "Tipo": label,
                "TWA inicio": "-", 
                "TWA fin": "-", 
                "UTC inicio": "-", 
                "UTC fin": "-",
                "VMG promedio": "-", 
                "Duración (s)": "-", 
                "Distancia (m)": "-"
            })
            continue

        idx_worst = -1
        if label == "ceñida":
            # Ceñida: buscar mínimo VMG promedio (más bajo)
            worst_vmg = float('inf')
            for idx in range(len(df_rango) - window + 1):
                vmg_prom = df_rango.loc[idx:idx+window-1, "VMG"].mean()
                if vmg_prom < worst_vmg:
                    worst_vmg = vmg_prom
                    idx_worst = idx
            vmg_val = worst_vmg
        else:
            # Popa: buscar máximo VMG promedio (menos negativo, más cercano a cero)
            worst_vmg = float('-inf')
            for idx in range(len(df_rango) - window + 1):
                vmg_prom = df_rango.loc[idx:idx+window-1, "VMG"].mean()
                if vmg_prom > worst_vmg:
                    worst_vmg = vmg_prom
                    idx_worst = idx
            vmg_val = worst_vmg

        tramo_worst = df_rango.loc[idx_worst:idx_worst+window-1]
        utc_ini_w = tramo_worst["UTC"].iloc[0]
        utc_fin_w = tramo_worst["UTC"].iloc[-1]
        twa_ini_w = tramo_worst["TWA"].iloc[0]
        twa_fin_w = tramo_worst["TWA"].iloc[-1]
        duracion_w = (pd.to_datetime(utc_fin_w) - pd.to_datetime(utc_ini_w)).total_seconds()
        distancia_w = tramo_worst["Dist"].sum()

        peor_tramos.append({
            "Track": track_labels[i], 
            "Tipo": label,
            "TWA inicio": f"{twa_ini_w:.1f}", 
            "TWA fin": f"{twa_fin_w:.1f}",
            "UTC inicio": pd.to_datetime(utc_ini_w).strftime("%H:%M:%S"),
            "UTC fin": pd.to_datetime(utc_fin_w).strftime("%H:%M:%S"),
            "VMG promedio": f"{vmg_val:.2f}",
            "Duración (s)": f"{duracion_w:.1f}", 
            "Distancia (m)": f"{distancia_w:.1f}"
        })

peor_tramos_df = pd.DataFrame(peor_tramos)
st.dataframe(peor_tramos_df, use_container_width=True)

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

    st.markdown("**Versión:** v1.2.1-beta  \n[Changelog](https://github.com/maxsail-project/maxsail-analytics/blob/main/CHANGELOG.md)")


