import os
import json
import io
import streamlit as st
import pandas as pd
import pydeck as pdk
import gpxpy

# --------- MAPTILER CONFIG ---------
MAPTILER_KEY = "1TpHMPPswY7nGJWlOXjY"
MAPTILER_STYLES = {
    "Base": f"https://api.maptiler.com/maps/backdrop/style.json?key={MAPTILER_KEY}",
    "Mapa": f"https://api.maptiler.com/maps/landscape/style.json?key={MAPTILER_KEY}",
    "Satélite": f"https://api.maptiler.com/maps/satellite/style.json?key={MAPTILER_KEY}",
}

st.set_page_config(page_title="maxSail Metadata Editor", layout="wide")
st.title("⛵ maxSail Metadata Editor")

# =========================
# INICIALIZACIÓN DE SESSION STATE
# =========================
# Metadatos (diccionario guardado en session_state["meta"])
meta = st.session_state.setdefault(
    "meta",
    {
        "TWD": 0,
        "TWDShift": 0,
        "TWS": 0,
        "TWSG": 0,
        "MINUTO_SALIDA": 5,
        "NOTAS": "",
    },
)

# Notas personales (texto libre)
st.session_state.setdefault("notas", meta.get("NOTAS", ""))

# Balizas confirmadas
st.session_state.setdefault("balizas", [])

# Baliza temporal
st.session_state.setdefault("baliza_temp", {})

# Flags de vista previa y bloqueo de autoupdate
st.session_state.setdefault("show_temp", False)
st.session_state.setdefault("baliza_locked", False)

# Tramos confirmados
st.session_state.setdefault("tramos", [])

# Tramo temporal
st.session_state.setdefault("tramo_temp", {})

# Flags de vista previa y bloqueo de autoupdate (tramos)
st.session_state.setdefault("show_tramo_temp", False)
st.session_state.setdefault("tramo_locked", False)

# Flag de importación de metadatos
st.session_state.setdefault("meta_imported", False)

# =========================
# 1) CARGA DE ARCHIVO GPX
# =========================
gpx_file = st.sidebar.file_uploader("Carga un archivo GPX", type=["gpx"])
if not gpx_file:
    st.info("Carga un GPX para comenzar.")
    st.stop()


@st.cache_data(show_spinner=False)
def gpx_to_df_bytes(content: bytes) -> pd.DataFrame:
    gpx = gpxpy.parse(content.decode("utf-8", errors="ignore"))
    data = []
    for track in gpx.tracks:
        for segment in track.segments:
            for pt in segment.points:
                data.append(
                    {
                        "Lat": pt.latitude,
                        "Lon": pt.longitude,
                        "UTC": pd.to_datetime(pt.time) if pt.time else None,
                    }
                )
    df = pd.DataFrame(data).dropna(subset=["UTC"]).reset_index(drop=True)
    return df


df = gpx_to_df_bytes(gpx_file.getvalue())
if df.empty:
    st.error("El archivo GPX no tiene puntos con UTC.")
    st.stop()

# Variables de tramo globales
t0, tf = df["UTC"].iloc[0], df["UTC"].iloc[-1]
duracion_total = int((tf - t0).total_seconds())
min_total = max(0, duracion_total // 60)
seg_total = duracion_total % 60

# ========================================
# 2) IMPORTAR METADATOS (ANTES DE WIDGETS)
# ========================================
st.sidebar.markdown("### Importar metadatos")

nombre_base = os.path.splitext(gpx_file.name)[0]
nombre_metadata = f"{nombre_base}-meta-data.json"
meta_file = st.sidebar.file_uploader(
    f"Archivo metadatos previo ({nombre_metadata})",
    type=["json"],
    key="meta_file",
)

if meta_file and not st.session_state.meta_imported:
    meta_loaded = json.load(meta_file)

    # Actualizar metadatos internos
    meta["TWD"] = int(meta_loaded.get("TWD", meta.get("TWD", 0)))
    meta["TWDShift"] = int(meta_loaded.get("TWDShift", meta.get("TWDShift", 0)))
    meta["TWS"] = int(meta_loaded.get("TWS", meta.get("TWS", 0)))
    meta["TWSG"] = int(meta_loaded.get("TWSG", meta.get("TWSG", 0)))
    meta["MINUTO_SALIDA"] = int(
        meta_loaded.get("MINUTO_SALIDA", meta.get("MINUTO_SALIDA", 5))
    )
    meta["NOTAS"] = meta_loaded.get("NOTAS", meta.get("NOTAS", ""))

    # Actualizar estado persistente
    st.session_state["notas"] = meta["NOTAS"]
    st.session_state["balizas"] = meta_loaded.get("BALIZAS", [])
    st.session_state["tramos"] = meta_loaded.get("TRAMOS", [])

    # Reset de estado temporal SOLO UNA VEZ
    st.session_state.baliza_temp = {}
    st.session_state.tramo_temp = {}
    st.session_state.pop("last_filter_sig", None)

    st.session_state.meta_imported = True
    st.success("Metadatos importados correctamente.")

if st.sidebar.button("🔄 Reimportar metadatos"):
    st.session_state.meta_imported = False
    st.sidebar.success("Metadatos listos para reimportar.")
    st.rerun()


# =========================================================
# 3) PREINICIALIZAR FILTRO Y CALCULAR df_filtro (ANTES LATERAL)
# =========================================================
# Defaults del filtro (para primer render y para que el sidebar siempre vea el tramo actual)
if "slider_rango" not in st.session_state:
    st.session_state.slider_rango = (0, min_total)
if "seg_ini" not in st.session_state:
    st.session_state.seg_ini = 0
if "seg_fin" not in st.session_state:
    st.session_state.seg_fin = seg_total

# Calcula tramo usando session_state actual
utc_ini = t0 + pd.Timedelta(
    minutes=int(st.session_state.slider_rango[0]),
    seconds=int(st.session_state.seg_ini),
)
utc_fin = t0 + pd.Timedelta(
    minutes=int(st.session_state.slider_rango[1]),
    seconds=int(st.session_state.seg_fin),
)
if utc_fin < utc_ini:
    # Corrige inversión
    utc_ini, utc_fin = utc_fin, utc_ini

df_filtro = df[(df["UTC"] >= utc_ini) & (df["UTC"] <= utc_fin)].reset_index(drop=True)
st.session_state.df_filtro = df_filtro  # accesible en sidebar

# =====================================
# 4) METADATOS (usa lo importado arriba)
# =====================================
st.sidebar.markdown("### Metadatos")

col_m1, col_m2 = st.sidebar.columns(2)
with col_m1:
    twd = st.number_input(
        "TWD (°)",
        0,
        359,
        int(meta.get("TWD", 0)),
        step=1,
        format="%d",
        key="twd",
    )
    twd = st.number_input(
        "TWDShift to (°)",
        0,
        359,
        int(meta.get("TWDShift", 0)),
        step=1,
        format="%d",
        key="twdshift",
    )
with col_m2:
    tws = st.number_input(
        "TWS (nudos)",
        0,
        60,
        int(meta.get("TWS", 0)),
        step=1,
        format="%d",
        key="tws",
    )
    twsg = st.number_input(
        "TWSG (gusts)",
        0,
        60,
        int(meta.get("TWSG", 0)),
        step=1,
        format="%d",
        key="twsg",
    )
minuto_salida = st.sidebar.number_input(
    "Minuto salida",
    0,
    9999,
    int(meta.get("MINUTO_SALIDA", 5)),
    step=1,
    format="%d",
    key="minuto_salida",
)

# Notas personales (usar session_state como fuente de verdad)
notas = st.sidebar.text_area("Notas personales", key="notas")

# Sincroniza meta con widgets actuales (session_state es la fuente de verdad)
meta.update(
    {
        "TWD": int(st.session_state.twd),
        "TWDShift": int(st.session_state.twdshift),
        "TWS": int(st.session_state.tws),
        "TWSG": int(st.session_state.twsg),
        "MINUTO_SALIDA": int(st.session_state.minuto_salida),
        "NOTAS": st.session_state["notas"],
    }
)

# ============================
# 5a) GESTIÓN DE BALIZAS
# ============================
st.sidebar.markdown("### Balizas")


def reset_baliza_temp() -> dict:
    # Usa df_filtro si existe; si no, primer punto del track
    if (
        "df_filtro" in st.session_state
        and isinstance(st.session_state.df_filtro, pd.DataFrame)
        and not st.session_state.df_filtro.empty
    ):
        lat = float(round(st.session_state.df_filtro["Lat"].iloc[0], 5))
        lon = float(round(st.session_state.df_filtro["Lon"].iloc[0], 5))
    else:
        lat = float(round(df["Lat"].iloc[0], 5))
        lon = float(round(df["Lon"].iloc[0], 5))
    return {
        "lat": lat,
        "lon": lon,
        "nombre": f"Baliza {len(st.session_state['balizas']) + 1}",
    }


if "baliza_temp" not in st.session_state or not st.session_state.baliza_temp:
    st.session_state.baliza_temp = reset_baliza_temp()
if "show_temp" not in st.session_state:
    st.session_state.show_temp = False
if "baliza_locked" not in st.session_state:
    st.session_state.baliza_locked = False

# ---- AUTO-SYNC de baliza con inicio del tramo si cambia el filtro ----
current_sig = (
    tuple(st.session_state.slider_rango),
    int(st.session_state.seg_ini),
    int(st.session_state.seg_fin),
)
if "last_filter_sig" not in st.session_state:
    st.session_state.last_filter_sig = current_sig

st.sidebar.checkbox("Bloquear autoupdate de baliza", key="baliza_locked")

if current_sig != st.session_state.last_filter_sig and not st.session_state.baliza_locked:
    if not st.session_state.df_filtro.empty:
        lat0 = float(round(st.session_state.df_filtro["Lat"].iloc[0], 5))
        lon0 = float(round(st.session_state.df_filtro["Lon"].iloc[0], 5))
        st.session_state.baliza_temp["lat"] = lat0
        st.session_state.baliza_temp["lon"] = lon0
        st.session_state["lat_b_new"] = lat0
        st.session_state["lon_b_new"] = lon0
    st.session_state.last_filter_sig = current_sig

# Edición de baliza temporal
col_b1, col_b2 = st.sidebar.columns(2)
with col_b1:
    _ = st.number_input(
        "Latitud",
        format="%.5f",
        step=0.00005,
        key="lat_b_new",
        value=st.session_state.baliza_temp["lat"],
    )
with col_b2:
    _ = st.number_input(
        "Longitud",
        format="%.5f",
        step=0.00005,
        key="lon_b_new",
        value=st.session_state.baliza_temp["lon"],
    )
_ = st.sidebar.text_input(
    "Nombre", key="nombre_b_new", value=st.session_state.baliza_temp["nombre"]
)

# Actualiza baliza temporal con lo ingresado
st.session_state.baliza_temp["lat"] = st.session_state.lat_b_new
st.session_state.baliza_temp["lon"] = st.session_state.lon_b_new
st.session_state.baliza_temp["nombre"] = st.session_state.nombre_b_new

# Botones
col_boton = st.sidebar.columns(3)
if col_boton[0].button("Agregar", key="baliza_add"):
    st.session_state.balizas.append(st.session_state.baliza_temp.copy())
    st.success(f"Baliza '{st.session_state.baliza_temp['nombre']}' agregada.")
    st.session_state.baliza_temp = reset_baliza_temp()

if col_boton[1].button("Limpiar", key="baliza_clear"):
    st.session_state.balizas = []

if col_boton[2].button("Vista previa", key="baliza_preview"):
    st.session_state.show_temp = not st.session_state.show_temp

# Edición de tabla de balizas
balizas_edit_df = (
    pd.DataFrame(st.session_state.balizas)
    if st.session_state.balizas
    else pd.DataFrame(columns=["lat", "lon", "nombre"])
)
if not balizas_edit_df.empty:
    st.sidebar.caption("✏️ Edita balizas en la tabla:")
    edit_df = st.sidebar.data_editor(
        balizas_edit_df, use_container_width=True, num_rows="dynamic", key="edit_balizas"
    )
    st.session_state.balizas = edit_df.to_dict(orient="records")

# ============================
# 5b) GESTIÓN DE TRAMOS
# ============================
st.sidebar.markdown("### Tramos de análisis")


def reset_tramo_temp() -> dict:
    return {
        "nombre": f"Tramo {len(st.session_state['tramos']) + 1}",
        "tipo": "Ceñida",
        "utc_ini": utc_ini.isoformat(),
        "utc_fin": utc_fin.isoformat(),
        "min_ini": int(st.session_state.slider_rango[0]),
        "seg_ini": int(st.session_state.seg_ini),
        "min_fin": int(st.session_state.slider_rango[1]),
        "seg_fin": int(st.session_state.seg_fin),
        "notas": "",
    }


if "tramo_temp" not in st.session_state or not st.session_state.tramo_temp:
    st.session_state.tramo_temp = reset_tramo_temp()
if "show_tramo_temp" not in st.session_state:
    st.session_state.show_tramo_temp = False
if "tramo_locked" not in st.session_state:
    st.session_state.tramo_locked = False

# ---- AUTO-SYNC de tramo con el filtro temporal ----
st.sidebar.checkbox("Bloquear autoupdate de tramo", key="tramo_locked")

if current_sig != st.session_state.last_filter_sig and not st.session_state.tramo_locked:
    st.session_state.tramo_temp["utc_ini"] = utc_ini.isoformat()
    st.session_state.tramo_temp["utc_fin"] = utc_fin.isoformat()
    st.session_state.tramo_temp["min_ini"] = int(st.session_state.slider_rango[0])
    st.session_state.tramo_temp["seg_ini"] = int(st.session_state.seg_ini)
    st.session_state.tramo_temp["min_fin"] = int(st.session_state.slider_rango[1])
    st.session_state.tramo_temp["seg_fin"] = int(st.session_state.seg_fin)

# ---- Edición de tramo temporal ----
st.session_state.tramo_temp["nombre"] = st.sidebar.text_input(
    "Nombre del tramo",
    value=st.session_state.tramo_temp["nombre"],
)

st.session_state.tramo_temp["tipo"] = st.sidebar.selectbox(
    "Tipo de tramo",
    ["Ceñida", "Popa", "Reach", "Salida", "Otro"],
    index=["Ceñida", "Popa", "Reach", "Salida", "Otro"].index(
        st.session_state.tramo_temp.get("tipo", "Ceñida")
    ),
)

# ---- Botones ----
col_t = st.sidebar.columns(3)
if col_t[0].button("Agregar tramo", key="tramo_add"):
    st.session_state.tramos.append(st.session_state.tramo_temp.copy())
    st.success(f"Tramo '{st.session_state.tramo_temp['nombre']}' agregado.")
    st.session_state.tramo_temp = reset_tramo_temp()

if col_t[1].button("Limpiar tramos", key="tramo_clear"):
    st.session_state.tramos = []

if col_t[2].button("Vista previa", key="tramo_preview"):
    st.session_state.show_tramo_temp = not st.session_state.show_tramo_temp

# ---- Edición de tabla de tramos ----
tramos_edit_df = (
    pd.DataFrame(st.session_state.tramos)
    if st.session_state.tramos
    else pd.DataFrame(
        columns=[
            "nombre",
            "tipo",
            "utc_ini",
            "utc_fin",
            "min_ini",
            "seg_ini",
            "min_fin",
            "seg_fin",
            "notas",
        ]
    )
)

if not tramos_edit_df.empty:
    st.sidebar.caption("✏️ Edita tramos en la tabla:")
    edit_df = st.sidebar.data_editor(
        tramos_edit_df,
        use_container_width=True,
        num_rows="dynamic",
        key="edit_tramos",
    )
    st.session_state.tramos = edit_df.to_dict(orient="records")

# ============================
# 6) EXPORTAR METADATOS
# ============================
st.sidebar.markdown("### Exportar metadatos")
meta_export = {
    **meta,
    "BALIZAS": st.session_state.balizas,
    "TRAMOS": st.session_state.tramos,
    "ARCHIVO_TRACK": gpx_file.name,
}

st.sidebar.download_button(
    f"Descargar {nombre_metadata}",
    data=json.dumps(meta_export, indent=2),
    file_name=nombre_metadata,
    mime="application/json",
)

# ======================================
# PANEL PRINCIPAL (MAPA ➜ FILTRO ➜ TABLA)
# ======================================

st.subheader("🗺️ Track y balizas en el mapa")

# Fondo de mapa (selector en el main panel)
fondo = st.selectbox("Fondo de mapa", list(MAPTILER_STYLES.keys()), index=0)
map_style = MAPTILER_STYLES[fondo]

# Helpers para capas
def _lines_from_df(dfi: pd.DataFrame):
    if len(dfi) < 2:
        return []
    seg = dfi[["Lon", "Lat"]].copy()
    seg["Lon_to"] = seg["Lon"].shift(-1)
    seg["Lat_to"] = seg["Lat"].shift(-1)
    seg = seg.dropna()
    return (
        seg.rename(
            columns={
                "Lon": "from_lon",
                "Lat": "from_lat",
                "Lon_to": "to_lon",
                "Lat_to": "to_lat",
            }
        ).to_dict("records")
    )


def crear_layers(df, df_filtro, balizas_df, baliza_temp_df, show_temp):
    layers = []
    # track completo
    if len(df) > 1:
        layers.append(
            pdk.Layer(
                "LineLayer",
                data=[
                    {
                        "from": [r["from_lon"], r["from_lat"]],
                        "to": [r["to_lon"], r["to_lat"]],
                    }
                    for r in _lines_from_df(df)
                ],
                get_source_position="from",
                get_target_position="to",
                get_color="[180,180,180]",
                get_width=2,
                pickable=False,
                name="Track original",
            )
        )
    # tramo filtrado
    if len(df_filtro) > 1:
        layers.append(
            pdk.Layer(
                "LineLayer",
                data=[
                    {
                        "from": [r["from_lon"], r["from_lat"]],
                        "to": [r["to_lon"], r["to_lat"]],
                    }
                    for r in _lines_from_df(df_filtro)
                ],
                get_source_position="from",
                get_target_position="to",
                get_color="[0,0,0]",
                get_width=4,
                pickable=False,
                name="Track recortado",
            )
        )
    # punto rojo 40% en inicio de tramo
    if not df_filtro.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=[
                    {
                        "lat": float(df_filtro.iloc[0]["Lat"]),
                        "lon": float(df_filtro.iloc[0]["Lon"]),
                        "name": "Inicio del tramo",
                    }
                ],
                get_position="[lon, lat]",
                get_color="[220,20,60,102]",  # 40% opacidad
                get_radius=7,
                pickable=True,
                name="Inicio del tramo",
            )
        )
    # balizas confirmadas
    if not balizas_df.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=balizas_df.assign(name=balizas_df.get("nombre", "Baliza")),
                get_position="[lon, lat]",
                get_color="[220,20,60]",
                get_radius=5,
                pickable=True,
                name="Balizas",
            )
        )
    # baliza temporal
    if show_temp and not baliza_temp_df.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=baliza_temp_df.assign(
                    name=baliza_temp_df.get("nombre", "Baliza temporal")
                ),
                get_position="[lon, lat]",
                get_color="[220,20,60,128]",
                get_radius=5,
                pickable=True,
                name="Baliza temporal",
            )
        )
    return layers


balizas_confirmadas_df = (
    pd.DataFrame(st.session_state.balizas)
    if st.session_state.balizas
    else pd.DataFrame(columns=["lat", "lon", "nombre"])
)
baliza_temp_df = (
    pd.DataFrame([st.session_state.baliza_temp])
    if st.session_state.show_temp
    else pd.DataFrame()
)
layers = crear_layers(
    df, df_filtro, balizas_confirmadas_df, baliza_temp_df, st.session_state.show_temp
)

if not df_filtro.empty:
    lat_center = float(df_filtro.iloc[0]["Lat"])
    lon_center = float(df_filtro.iloc[0]["Lon"])
else:
    lat_center = float(df["Lat"].mean())
    lon_center = float(df["Lon"].mean())

tooltip = {"text": "{name}"}

st.pydeck_chart(
    pdk.Deck(
        map_style=map_style,
        initial_view_state=pdk.ViewState(
            latitude=lat_center,
            longitude=lon_center,
            zoom=14,
            pitch=0,
            bearing=float(meta.get("TWD", 0)),
        ),
        layers=layers,
        tooltip=tooltip,
    )
)

# --- Filtro temporal debajo del mapa ---
with st.container():
#    st.markdown("### Selección de tramo temporal")
    col_time1, col_time2, col_time3 = st.columns([3, 1, 1])
    with col_time1:
        _ = st.slider(
            "Rango de minutos del track",
            0,
            min_total,
            st.session_state.slider_rango,
            step=1,
            key="slider_rango",
        )
    with col_time2:
        _ = st.number_input(
            "Segundos inicio",
            0,
            59,
            st.session_state.seg_ini,
            step=5,
            format="%d",
            key="seg_ini",
        )
    with col_time3:
        _ = st.number_input(
            "Segundos fin",
            0,
            59,
            st.session_state.seg_fin,
            step=5,
            format="%d",
            key="seg_fin",
        )

# ======================================
# TABLAS RESUMEN BAJO EL MAPA
# ======================================

st.markdown("### 📋 Resumen de elementos definidos")

# ---------- BALIZAS ----------
if not balizas_confirmadas_df.empty:
    st.markdown("#### 📍 Balizas confirmadas")

    balizas_view = balizas_confirmadas_df.copy()
    try:
        balizas_view["Lat"] = balizas_view["lat"].map(lambda x: f"{x:.5f}")
        balizas_view["Lon"] = balizas_view["lon"].map(lambda x: f"{x:.5f}")
    except Exception as e:
        print("DEBUG error creando columnas Lat/Lon:", e)

    st.dataframe(
        balizas_view[["nombre", "Lat", "Lon"]],
        use_container_width=True,
        hide_index=True,
    )

# ---------- TRAMOS ----------
if st.session_state.tramos:
    st.markdown("#### ⏱️ Tramos de análisis")

    tramos_view = pd.DataFrame(st.session_state.tramos).copy()

    # Formato mm:ss para inicio y fin
    tramos_view["inicio (mm:ss)"] = tramos_view.apply(
        lambda r: f"{int(r['min_ini']):02d}:{int(r['seg_ini']):02d}",
        axis=1
    )

    tramos_view["fin (mm:ss)"] = tramos_view.apply(
        lambda r: f"{int(r['min_fin']):02d}:{int(r['seg_fin']):02d}",
        axis=1
    )

    st.dataframe(
        tramos_view[
            ["nombre", "tipo", "inicio (mm:ss)", "fin (mm:ss)", "utc_ini", "utc_fin"]
        ],
        use_container_width=True,
        hide_index=True,
    )


# ---------- EMPTY STATE ----------
if balizas_confirmadas_df.empty and not st.session_state.tramos:
    st.info("No hay balizas ni tramos definidos todavía.")

# ============================
# 7) PROYECTO ABIERTO Y DESCARGO DE RESPONSABILIDAD
# ============================
st.markdown("""
---
#### 📢 Proyecto abierto y descargo de responsabilidad
            
Este editor de metadatos de regatas forma parte del ecosistema **maxSail-Project**. Es un proyecto **abierto y experimental**, orientado a la preparación, análisis y reutilización de información asociada a tracks / GPX.
Permite definir y editar **balizas, tramos y metadatos** para su posterior uso en herramientas de análisis como *maxSail-Analytics*.

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
    **maxSail-meta-data**
    - Autor: Maximiliano Mannise
    - [maxsail.project@gmail.com](mailto:maxsail.project@gmail.com)
    - [GitHub: maxsail-project](https://github.com/maxsail-project)
    """)
