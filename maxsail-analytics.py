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
from collections import deque
import altair as alt
import pydeck as pdk

from utils import (
    calculate_distance_bearing,
    calculate_velocity,
    estimate_twa,
    calculate_vmg,
    estimate_wind_direction,
    gpx_file_to_df
)

# -----------------------------
# INICIO APP STREAMLIT
# -----------------------------
st.set_page_config(page_title="Visor de Regata GPX/CSV", layout="wide")
st.title("🚩 maxSail : Sailing Data, Better Decisions")

uploaded_files = st.sidebar.file_uploader(
    "Selecciona uno o más archivos GPX o CSV", 
    type=["gpx", "csv"], 
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Sube al menos un archivo GPX o CSV para comenzar.")
    st.markdown("""
# maxSail-analytics

**Visor y analizador open source de tracks GPS para regatas y entrenamientos de vela ligera.**

Sube uno o varios archivos GPX o CSV para analizar, comparar y visualizar tus navegaciones.

Contacto:
- Name: Maximiliano Mannise
- Email: maxsail.project@gmail.com
- GitHub: https://github.com/maxsail-project/maxsail-analytics 

---

*Este proyecto es open source, ¡colaboraciones y sugerencias bienvenidas!*  
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

df1 = df[df['SourceFile'] == track1].copy() if track1 != "(Ninguno)" else pd.DataFrame()
df2 = df[df['SourceFile'] == track2].copy() if track2 != "(Ninguno)" else pd.DataFrame()

if df1.empty and df2.empty:
    st.info("Selecciona al menos un track para comenzar.")
    st.stop()

# --- Ingreso manual de TWD ---
twd = st.sidebar.number_input(
    "TWD (True Wind Direction, ° estimada)", min_value=0, max_value=360, value=0, step=5
)

def minsec(minutes_float):
    mins = int(minutes_float)
    secs = int(round((minutes_float - mins)*60))
    return f"{mins}:{secs:02d}"

def to_minutes(mins, secs):
    return mins + secs/60

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

min_ini = st.sidebar.number_input("Minuto inicial", min_value=0, max_value=int(min_duration), value=min_ini, step=1)
min_fin = st.sidebar.number_input("Minuto final", min_value=0, max_value=int(min_duration), value=min_fin, step=1)
sec_ini = st.sidebar.number_input("Segundo inicial", min_value=0, max_value=59, value=sec_ini, step=5)
sec_fin = st.sidebar.number_input("Segundo final", min_value=0, max_value=59, value=sec_fin, step=5)

start_min = to_minutes(min_ini, sec_ini)
end_min = to_minutes(min_fin, sec_fin)
if start_min >= end_min:
    end_min = min(start_min + 0.5, float(min_duration))
start_min, end_min = st.sidebar.slider(
    "Tramo seleccionado",
    0.0, float(min_duration),
    (start_min, end_min),
    step=0.5
)

st.sidebar.info(
    "El selector utiliza minutos con decimales; cada decimal representa segundos.\n"
    "Por ejemplo: **2.50** son **2 minutos 30 segundos**."
)

def filtrar_por_tiempo(df, start_min, end_min):
    t0 = df['UTC'].iloc[0]
    df = df.copy()
    df['minutes'] = (df['UTC'] - t0).dt.total_seconds() / 60
    return df[(df['minutes'] >= start_min) & (df['minutes'] <= end_min)].copy()

def calcular_twa_vmg(df, twd):
    if df.empty:
        return df
    df['TWA'] = np.abs(df['COG'] - twd)
    df['TWA'] = df['TWA'].apply(lambda x: 360-x if x > 180 else x)
    df['VMG'] = df['SOG'] * np.cos(np.radians(df['TWA']))
    return df

if not df1.empty:
    df1 = filtrar_por_tiempo(df1, start_min, end_min)
    df1 = calcular_twa_vmg(df1, twd)
if not df2.empty:
    df2 = filtrar_por_tiempo(df2, start_min, end_min)
    df2 = calcular_twa_vmg(df2, twd)

if df1.empty and df2.empty:
    st.warning("El tramo seleccionado no contiene datos en uno o ambos tracks. Ajusta el tramo para ver los análisis.")
    st.stop()

# --- MAPA ---
st.subheader("📍 Mapa - visualización de tracks")
layers = []
if not df1.empty:
    line_data1 = []
    for i in range(1, len(df1)):
        p1 = df1.iloc[i - 1]
        p2 = df1.iloc[i]
        line_data1.append({
            "from": [p1['Lon'], p1['Lat']],
            "to": [p2['Lon'], p2['Lat']],
            "color": [0, 100, 255]
        })
    layers += [
        pdk.Layer('LineLayer', data=line_data1, get_source_position='from', get_target_position='to', get_color='color', get_width=3),
        pdk.Layer('ScatterplotLayer', data=[{"Latitude": df1.iloc[0]['Lat'], "Longitude": df1.iloc[0]['Lon']}], get_position='[Longitude, Latitude]', get_color='[0, 255, 0]', get_radius=15),
        pdk.Layer('ScatterplotLayer', data=[{"Latitude": df1.iloc[-1]['Lat'], "Longitude": df1.iloc[-1]['Lon']}], get_position='[Longitude, Latitude]', get_color='[255, 0, 0]', get_radius=15)
    ]
if not df2.empty:
    line_data2 = []
    for i in range(1, len(df2)):
        p1 = df2.iloc[i - 1]
        p2 = df2.iloc[i]
        line_data2.append({
            "from": [p1['Lon'], p1['Lat']],
            "to": [p2['Lon'], p2['Lat']],
            "color": [255, 100, 0]
        })
    layers += [
        pdk.Layer('LineLayer', data=line_data2, get_source_position='from', get_target_position='to', get_color='color', get_width=2),
        pdk.Layer('ScatterplotLayer', data=[{"Latitude": df2.iloc[0]['Lat'], "Longitude": df2.iloc[0]['Lon']}], get_position='[Longitude, Latitude]', get_color='[0, 255, 255]', get_radius=15),
        pdk.Layer('ScatterplotLayer', data=[{"Latitude": df2.iloc[-1]['Lat'], "Longitude": df2.iloc[-1]['Lon']}], get_position='[Longitude, Latitude]', get_color='[255, 255, 0]', get_radius=15)
    ]
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

st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox//dark-v10',
        initial_view_state=pdk.ViewState(
        latitude=lat_mean,
        longitude=lon_mean,
        zoom=14,
        pitch=0,
        bearing=twd
    ),
    layers=layers,
    tooltip={"html": "<b>SOG:</b> {SOG} knots<br><b>Hora:</b> {UTC}<br><b>COG:</b> {COG}°"},
))

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

# ----------------------------
# --- MÉTRICAS PRINCIPALES ---
# ----------------------------
st.subheader("📊 Métricas principales")

metrics = [
    ("SOG promedio (knots)", lambda df: f"{df['SOG'].mean():.2f}" if not df.empty else "-"),
    ("SOG máxima (knots)", lambda df: f"{df['SOG'].max():.2f}" if not df.empty else "-"),
    ("TWA medio* (°)", lambda df: f"{df['TWA'].mean():.1f}" if not df.empty else "-"),
    ("VMG promedio (knots)", lambda df: f"{df['VMG'].mean():.2f}" if not df.empty else "-"),
    ("Distancia (nm)", lambda df: f"{df['Dist'].sum() / 1852:.2f}" if not df.empty else "-"),
    ("Duración (min)", lambda df: f"{(df['UTC'].iloc[-1] - df['UTC'].iloc[0]).total_seconds()/60:.1f}" if not df.empty and len(df) > 1 else "-"),
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

# --- Construye la tabla base ---
tabla_metricas = {}
for label, df in zip(track_labels, track_dfs):
    valores = [calc(df) for _, calc in metrics]
    tabla_metricas[label] = valores

tabla_metricas_df = pd.DataFrame(tabla_metricas, index=[m[0] for m in metrics])

# --- Calcula distancias absolutas en metros ---
dist_metros = [df['Dist'].sum() if not df.empty else np.nan for df in track_dfs]
dist_min = np.nanmin(dist_metros)

# --- Calcula diferencia con mínima distancia para cada track ---
diferencias = []
for i, dist in enumerate(dist_metros):
    if np.isnan(dist):
        diferencias.append("-")
    else:
        valor = dist - dist_min
        if valor == 0:
            diferencias.append("0 (mínimo)")
        else:
            diferencias.append(f"{valor:,.1f} m")

# --- Añade la fila a la tabla ---
tabla_metricas_df.loc["Diferencia con mínima distancia (m)"] = diferencias

# --- Formato visual (color de encabezados) ---
styled = tabla_metricas_df.style
for label, color in zip(track_labels, track_colors):
    styled = styled.set_properties(subset=[label], **{'color': color, 'font-weight': 'bold'})

st.markdown("#### Comparativa por Track")
st.dataframe(styled, use_container_width=False)

st.caption("* TWA y VMG calculados según el TWD ingresado manualmente")
st.divider()

# --- EVOLUCIÓN DE SOG ---
st.subheader("📈 Evolución de SOG (knots)")
if not df_plot.empty:
    chart_sog = alt.Chart(df_plot).mark_line().encode(
        x=alt.X('UTC:T', title='Tiempo'),
        y=alt.Y('SOG:Q', title='SOG (knots)'),
        color=alt.Color('Track:N', scale=color_scale, legend=alt.Legend(title="Track"))
    ).properties(width=900, height=250)
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
        sog_avg = f"{track_df['SOG'].mean():.2f} ({track_df['TWA'].mean():.1f}°)"
    else:
        sog_max = sog_min = sog_avg = "-"
    sog_data[track_label] = [sog_max, sog_min, sog_avg]

tabla_sog = pd.DataFrame(
    sog_data,
    index=["SOG máximo knots (TWA)", "SOG mínimo knots (TWA)", "SOG promedio knots (TWA medio)"]
)

st.dataframe(tabla_sog, use_container_width=True)

# --- EVOLUCIÓN DE COG ---
st.subheader("📈 Evolución de COG (°)")
if not df_plot.empty:
    chart_cog = alt.Chart(df_plot).mark_line().encode(
        x=alt.X('UTC:T', title='Tiempo'),
        y=alt.Y('COG:Q', title='COG (°)'),
        color=alt.Color('Track:N', scale=color_scale, legend=alt.Legend(title="Track"))
    ).properties(width=900, height=250)
    st.altair_chart(chart_cog, use_container_width=True)

cog_data = {}
for track_label, track_df in zip(track_labels, track_dfs):
    if not track_df.empty and not track_df['COG'].isnull().all():
        cog_min = f"{track_df['COG'].min():.1f}"
        cog_max = f"{track_df['COG'].max():.1f}"
        cog_avg = f"{track_df['COG'].mean():.1f}"
        cog_std = f"{track_df['COG'].std():.1f}"
    else:
        cog_min = cog_max = cog_avg = cog_std = "-"
    cog_data[track_label] = [cog_min, cog_max, cog_avg, cog_std]

tabla_cog = pd.DataFrame(
    cog_data,
    index=["Mínimo", "Máximo", "Promedio", "Dispersión (std)"]
)

st.dataframe(tabla_cog, use_container_width=True)

st.caption(
        "Si es baja → el barco mantuvo rumbo muy estable. Si es alta → hubo cambios de rumbo (maniobras, zigzags, etc)"
    )

# --- EVOLUCIÓN DE VMG ---
st.subheader("📈 Evolución de VMG (knots)")
if not df_plot.empty and 'VMG' in df_plot.columns:
    chart_vmg = alt.Chart(df_plot).mark_line().encode(
        x=alt.X('UTC:T', title='Tiempo'),
        y=alt.Y('VMG:Q', title='VMG (knots)'),
        color=alt.Color('Track:N', scale=color_scale)
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
        vmg_avg = f"{track_df['VMG'].mean():.2f} ({track_df['TWA'].mean():.1f}°)"
    else:
        vmg_max = vmg_min = vmg_avg = "-"
    vmg_data[track_label] = [vmg_max, vmg_min, vmg_avg]

# Construye el DataFrame resumen
tabla_vmg = pd.DataFrame(
    vmg_data,
    index=["VMG máximo knots, (TWA)", "VMG mínimo knots (TWA)", "VMG promedio knots (TWA medio)"]
)
st.dataframe(tabla_vmg, use_container_width=True)

# --- EVOLUCIÓN DE TWA ---
st.subheader("📈 Evolución de TWA (°)")
if not df_plot.empty and 'TWA' in df_plot.columns:
    chart_twa = alt.Chart(df_plot).mark_line().encode(
        x=alt.X('UTC:T', title='Tiempo'),
        y=alt.Y('TWA:Q', title='TWA (°)'),
        color=alt.Color('Track:N', scale=color_scale)
    ).properties(width=900, height=250)
    st.altair_chart(chart_twa, use_container_width=True)

# --- HISTOGRAMA DE SOG (agrupado si hay dos tracks) ---
st.subheader("📊 Histograma de SOG (knots)")
if not df_plot.empty:
    if not df1_plot.empty and not df2_plot.empty:
        hist_sog = alt.Chart(df_plot).mark_bar(size=30, opacity=0.7).encode(
            x=alt.X('SOG:Q', bin=alt.Bin(maxbins=25), title='SOG (knots)'),
            y=alt.Y('count()', stack=None, title='Frecuencia'),
            color=alt.Color('Track:N', scale=color_scale, legend=alt.Legend(title="Track")),
            xOffset='Track:N',
            tooltip=['count()', 'Track:N']
        ).properties(width=900, height=250)
    else:
        hist_sog = alt.Chart(df_plot).mark_bar(size=25, opacity=0.7).encode(
            x=alt.X('SOG:Q', bin=alt.Bin(maxbins=25), title='SOG (knots)'),
            y=alt.Y('count()', stack=None, title='Frecuencia'),
            color=alt.Color('Track:N', scale=color_scale),
            tooltip=['count()']
        ).properties(width=900, height=250)
    st.altair_chart(hist_sog, use_container_width=True)

# --- DISPERSIÓN SOG vs TWA ---
st.subheader("📊 SOG vs. TWA (dispersión)")
if not df_plot.empty and 'TWA' in df_plot.columns:
    scatter_sog_twa = alt.Chart(df_plot).mark_circle(size=45, opacity=0.6).encode(
        x=alt.X('TWA:Q', title='TWA (°)'),
        y=alt.Y('SOG:Q', title='SOG (knots)'),
        color=alt.Color('Track:N', scale=color_scale, legend=alt.Legend(title="Track")),
        tooltip=['UTC:T', 'SOG:Q', 'TWA:Q', 'Track:N']
    ).properties(width=900, height=300)
    st.altair_chart(scatter_sog_twa, use_container_width=True)

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
        x=alt.X('TWA:Q', title='TWA (°)'),
        y=alt.Y('VMG:Q', title='VMG (knots)'),
        color=alt.Color('Track:N', scale=color_scale, legend=alt.Legend(title="Track")),
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
    min_value=5, max_value=60, value=15, step=1,
    help="Descarta maniobras consecutivas muy cercanas en el tiempo"
)

maniobra_points = []
if not df_plot.empty:
    for track in df_plot['Track'].unique():
        track_df = df_plot[df_plot['Track'] == track].sort_values('UTC').reset_index(drop=True)
        cogs = track_df['COG'].values
        times = track_df['UTC'].values
        for i in range(window, len(cogs) - window):  # ¡IMPORTANTE! evita error en ventana post
            ventana_prev = cogs[i-window:i]
            ventana_post = cogs[i+1:i+1+window]
            media_prev = np.mean(ventana_prev)
            media_post = np.mean(ventana_post)
            mediana_prev = np.median(ventana_prev)
            diff = abs(cogs[i] - mediana_prev)
            if diff > 180:
                diff = 360 - diff
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

# Eliminar maniobras cercanas en el tiempo
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
chart_cog = alt.Chart(df_plot).mark_line().encode(
    x=alt.X('UTC:T', title='Tiempo'),
    y=alt.Y('COG:Q', title='COG (°)'),
    color=alt.Color('Track:N', scale=color_scale, legend=alt.Legend(title="Track"))
)
if not maniobra_df.empty:
    points = alt.Chart(maniobra_df).mark_point(
        shape='triangle-up', color='red', size=120
    ).encode(
        x='UTC:T',
        y='COG:Q',
        tooltip=['UTC:T', 'COG:Q', 'Track:N']
    )
    chart_final = chart_cog + points
    st.altair_chart(chart_final.properties(width=900, height=250), use_container_width=True)
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
        value="-12,-8,-5,-3,-2,-1,0,1,2,3,5,8,12,20"
    )
    try:
        ventanas = [int(s) for s in ventana_input.replace(' ', '').split(',') if s]
        ventanas = sorted(set(ventanas))
    except Exception as e:
        st.error(f"Error en las ventanas: {e}")
        ventanas = [0]
    ventana_labels = [f"{n:+d}s" if n != 0 else "0s" for n in ventanas]
    tabla = []
    for idx, maniobra in maniobra_df.iterrows():
        track = maniobra["Track"]
        time = maniobra["UTC"]
        df_este_track = df_plot[df_plot["Track"] == track]
        delta_cog = ((maniobra["COG_post"] - maniobra["COG_previo"] + 180) % 360) - 180
        delta_cog = round(delta_cog, 0)
        for delta, label in zip(ventanas, ventana_labels):
            if delta == 0:
                rango = (time - pd.Timedelta(seconds=0.5), time + pd.Timedelta(seconds=0.5))
            elif delta < 0:
                rango = (time + pd.Timedelta(seconds=delta), time)
            else:
                rango = (time, time + pd.Timedelta(seconds=delta))
            vel_media = df_este_track[
                (df_este_track["UTC"] >= rango[0]) & (df_este_track["UTC"] <= rango[1])
            ]["SOG"].mean()
            tabla.append({
                "Track": track,
                "Momento": time.strftime("%H:%M:%S"),
                "COG previo": round(maniobra["COG_previo"], 0),
                "COG post": round(maniobra["COG_post"], 0),
                "Delta COG": delta_cog,
                label: f"{vel_media:.2f}" if not np.isnan(vel_media) else "-"
            })

        tabla_df = pd.DataFrame(tabla)
        tabla_df_pivot = tabla_df.pivot_table(
            index=["Track", "Momento", "COG previo", "COG post", "Delta COG"],
            values=ventana_labels,
            aggfunc='first'
        ).reset_index()

        columnas_finales = ["Track", "Momento", "COG previo", "COG post", "Delta COG"] + ventana_labels
        tabla_df_pivot = tabla_df_pivot.reindex(columns=columnas_finales)

    st.markdown("#### Tabla: velocidad media antes y después de cada maniobra (COG previo y post = media de ventana antes y después del giro)")
    st.dataframe(tabla_df_pivot, hide_index=True, use_container_width=True)


### PoC st.caption("SOG en naranja, COG en gris.")


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
    **maxsail-analytics**
    - Autor: Maximiliano Mannise
    - Email: [maxsail.project@gmail.com](mailto:maxsail.project@gmail.com)
    - [GitHub](https://github.com/maxsail-project)
    """)
