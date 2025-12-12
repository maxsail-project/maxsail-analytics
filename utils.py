# utils.py
import math
import pandas as pd
import gpxpy
import pyproj 
import numpy as np

from haversine import haversine
from pyproj import Proj, Transformer

wgs84 = pyproj.Geod(ellps="WGS84")

# --- Geodesia avanzada con pyproj ---
def puntos_perpendiculares_pyproj(lat, lon, twd_degrees, distancia_m=100):
    """Devuelve dos puntos a distancia_m a cada lado del punto base, en la perpendicular al viento (TWD), usando pyproj."""
    left = (twd_degrees - 90) % 360
    right = (twd_degrees + 90) % 360
    lon1, lat1, _ = wgs84.fwd(lon, lat, left, distancia_m)
    lon2, lat2, _ = wgs84.fwd(lon, lat, right, distancia_m)
    return [(lat1, lon1), (lat2, lon2)]

def linea_perpendicular_pyproj(lat, lon, twd, distancia_m=20):
    """Devuelve las coordenadas de los extremos de una línea centrada en (lat, lon) perpendicular al viento (TWD)."""
    return puntos_perpendiculares_pyproj(lat, lon, twd, distancia_m)

def normalize_angle(angle):
    """Normaliza cualquier ángulo a [0, 360)."""
    return angle % 360

def angle_diff(a, b):
    """
    Diferencia angular mínima (en grados) entre dos rumbos a y b.
    Devuelve valor entre 0 y 180.
    """
    d = abs(normalize_angle(a - b))
    return d if d <= 180 else 360 - d

def calcular_twa_vmg(df, twd):
    """
    Añade columnas TWA (True Wind Angle) y VMG (Velocity Made Good) al DataFrame,
    según TWD (True Wind Direction) y los campos COG y SOG del dataframe.
    TWA con signo [-180, 180]. positvo amurado a babor, negativo a estribor.
    TWA_abs en [0, 180].
    VMG con signo: positivo hacia el viento, negativo alejándose.
    """
    if df.empty:
        return df
    # TWA firmado en [-180, +180]
    TWA_signed = ((df['COG'] - twd + 180) % 360) - 180
    df['TWA'] = TWA_signed                  # mantiene compatibilidad con el resto del código
    df['TWA_abs'] = np.abs(TWA_signed)      # útil para gráficos en magnitud
    df['VMG'] = df['SOG'] * np.cos(np.radians(TWA_signed))  # igual con firmado o absoluto
    return df

def calculate_distance_bearing(lat1, lon1, lat2, lon2):
    """Calcula distancia y rumbo entre dos puntos geográficos."""
    bearing_to, bearing_back, distance = wgs84.inv(lon1, lat1, lon2, lat2)
    return distance, (bearing_to + 360) % 360, (bearing_back + 360) % 360

def calculate_velocity(lat1, lon1, lat2, lon2, time_in_seconds):
    """Calcula velocidad en nudos entre dos puntos y un delta de tiempo."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    earth_radius = 3440.065
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    a = (math.sin(delta_lat / 2) ** 2) + math.cos(lat1) * math.cos(lat2) * (math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_in_nm = earth_radius * c
    time_in_hours = time_in_seconds / 3600.0
    return distance_in_nm / time_in_hours if time_in_hours > 0 else 0

def estimate_twa(boat_heading, TWD):
    """Calcula el ángulo real al viento (TWA)."""
    delta = (TWD - boat_heading + 360) % 360
    if delta > 180:
        delta -= 360
    return round(delta, 1)

def calculate_vmg(SOG, TWA):
    """Calcula el Velocity Made Good."""
    twa_rad = math.radians(TWA)
    VMG = SOG * math.cos(twa_rad)
    return round(VMG, 2)

def estimate_wind_direction(lat_start, lon_start, lat_end, lon_end):
    """Estima la dirección del viento a partir del recorrido."""
    _, COG, _ = calculate_distance_bearing(lat_start, lon_start, lat_end, lon_end)
    return (COG + 180) % 360

def gpx_file_to_df(gpx_file, file_name):
    """Convierte un archivo GPX en un DataFrame normalizado para el visor.
    - Normaliza timestamps para calcular time_diff correctamente.
    - Elimina puntos duplicados exactos (lat/lon).
    - Calcula Dist, COG, SOG, TWA y VMG.
    - Gestiona prev_point para evitar picos falsos de velocidad.
    - Devuelve un DataFrame limpio listo para el visor.
    """
    gpx = gpxpy.parse(gpx_file)
    rows = []
    prev_point = None
    first_point = None
    last_point = None

    # Buscar primer y último punto
    for track in gpx.tracks:
        for segment in track.segments:
            if segment.points:
                first_point = segment.points[0]
                last_point = segment.points[-1]
    if not first_point or not last_point:
        return pd.DataFrame()
    TWD = estimate_wind_direction(first_point.latitude, first_point.longitude, last_point.latitude, last_point.longitude)
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                # Inicializar prev_point en el primer punto válido
                if prev_point is None:
                    prev_point = point
                    continue
                # Saltar puntos duplicados
                if point.latitude == prev_point.latitude and point.longitude == prev_point.longitude:
                    continue
                lat, lon = point.latitude, point.longitude
                distance, COG, _ = calculate_distance_bearing(prev_point.latitude, prev_point.longitude, lat, lon)

                # Normalizar timestamps para evitar mezcla UTC/naive
                curr_time = point.time.replace(tzinfo=None)
                prev_time = prev_point.time.replace(tzinfo=None)

                time_diff = (curr_time - prev_time).total_seconds()
                SOG = calculate_velocity(prev_point.latitude, prev_point.longitude, lat, lon, time_diff)
                UTC = curr_time
                TWA = estimate_twa(COG, TWD)
                VMG = calculate_vmg(SOG, TWA)
                # Construir fila del DataFrame track
                row = {
                    'Lat': lat,
                    'Lon': lon,
                    'UTC': UTC,
                    'COG': round(COG),
                    'SOG': round(SOG, 2),
                    'Dist': round(distance, 2),
                    'SourceFile': file_name,
                    'TWA': TWA,
                    'VMG': VMG,
                }
                rows.append(row)
                # Actualizar prev_point para el siguiente loop
                prev_point = point

    df = pd.DataFrame(rows)

    if not df.empty and 'UTC' in df.columns:
        df['UTC'] = pd.to_datetime(df['UTC']).dt.tz_localize(None)

    # --- SOG smooth / suavizada (SOGS) ---
    if not df.empty and 'SOG' in df.columns:
        # Media móvil de 5 puntos (centrada)
        df['SOGS'] = df['SOG'].rolling(window=5, center=True, min_periods=1).mean()

    return df


def distance_on_axis(lat1, lon1, lat2, lon2, axis_deg):
    """
    Devuelve la distancia (en metros) entre dos puntos GPS, proyectada sobre un eje dado (axis_deg, en grados desde el norte).
    El resultado tiene signo: positivo si p2 está adelante en el eje, negativo si p1 está adelante.
    """
    R = 6371000  # Radio de la Tierra en metros
    # Convertir desplazamientos a metros (proyección local)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    lat_med = np.radians((lat1 + lat2)/2)
    xm = R * dlon * np.cos(lat_med)
    ym = R * dlat

    # Vector unitario del eje deseado
    az = np.radians(axis_deg % 360)
    ux, uy = np.sin(az), np.cos(az)
    # Proyección sobre ese eje
    dist_axis = xm * ux + ym * uy
    return dist_axis  # metros

def distance_on_ladder(lat1, lon1, lat2, lon2, twd_deg):
    """
    Calcula la distancia mínima (en metros) entre la recta perpendicular al viento (peldaño)
    que pasa por (lat1, lon1) y el punto (lat2, lon2).
    Signo: positivo si lat2/lon2 está a barlovento de lat1/lon1, negativo si a sotavento.
    """
    R = 6371000 # Radio de la Tierra en metros
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    xm = R * dlon * np.cos(np.radians((lat1 + lat2) / 2))
    ym = R * dlat

    # Dirección viento en radianes
    twd_rad = np.radians(twd_deg % 360)
    # Vector unitario del viento (eje principal)
    u_wind = np.array([np.sin(twd_rad), np.cos(twd_rad)])
    # Vector barco1 -> barco2
    v = np.array([xm, ym])
    # Proyección sobre el eje viento
    avance = np.dot(v, u_wind)
    # Vector ortogonal desde barco2 a la recta del peldaño de barco1
    v_ort = v - avance * u_wind
    # Distancia mínima entre el punto y la recta (peldaño)
    dist_ladder = np.linalg.norm(v_ort)
    # Signo: positivo si barco2 está a barlovento de barco1, negativo si a sotavento
    sign = np.sign(np.cross(u_wind, v_ort))
    return sign * dist_ladder

def ladder_position(lat, lon, lat_ref, lon_ref, twd_deg):
    """
    Proyección (en metros) de un punto sobre el eje perpendicular al viento,
    respecto a un origen (lat_ref, lon_ref).
    """
    R = 6371000 # Radio de la Tierra en metros
    dlat = np.radians(lat - lat_ref)
    dlon = np.radians(lon - lon_ref)
    xm = R * dlon * np.cos(np.radians((lat + lat_ref) / 2))
    ym = R * dlat
    twd_perp_rad = np.radians((twd_deg + 90) % 360)
    u_perp = np.array([np.sin(twd_perp_rad), np.cos(twd_perp_rad)])
    v = np.array([xm, ym])
    pos_ladder = np.dot(v, u_perp)
    return pos_ladder

def ladder_distance(lat1, lon1, lat2, lon2, twd_deg, lat_ref=None, lon_ref=None):
    """
    Devuelve la distancia entre los peldaños de ambos barcos a la misma altura sobre el viento.
    Por defecto usa el barco 1 como referencia de origen.
    """
    if lat_ref is None: lat_ref = lat1
    if lon_ref is None: lon_ref = lon1
    pos1 = ladder_position(lat1, lon1, lat_ref, lon_ref, twd_deg)
    pos2 = ladder_position(lat2, lon2, lat_ref, lon_ref, twd_deg)
    return pos2 - pos1  # metros (positivo: barco 2 más a barlovento)

def ladder_distance_utm(lat1, lon1, lat2, lon2, twd_deg, utm_zone=None):
    """
    Distancia barlovento/sotavento (en metros) usando UTM.
    Si utm_zone no se especifica, se deduce automáticamente a partir de lon1.
    """
    if utm_zone is None: 
        utm_zone = int((lon1 + 180) / 6) + 1
    p = Proj(proj='utm', zone=utm_zone, ellps='WGS84')
    x1, y1 = p(lon1, lat1)
    x2, y2 = p(lon2, lat2)
    theta = np.radians(twd_deg + 90)
    u_x = np.cos(theta)
    u_y = np.sin(theta)
    delta_x = x2 - x1
    delta_y = y2 - y1
    dist_perpendicular = delta_x * u_x + delta_y * u_y
    return dist_perpendicular

def ladder_distance_rung(lat1, lon1, lat2, lon2, twd_deg):
    # 1. Conversión Lat/Lon → UTM ------------------
    tf = Transformer.from_crs("EPSG:4326", "EPSG:25829", always_xy=True)
    x1, y1 = tf.transform(lon1, lat1)
    x2, y2 = tf.transform(lon2, lat2)

    # 2. Vectores unitarios ------------------------
    θ = math.radians(twd_deg)
    p_x = -math.cos(θ)   # componente Este del perpendicular
    p_y =  math.sin(θ)   # componente Norte del perpendicular

    # 3. Proyecciones ------------------------------
    d1 = x1 * p_x + y1 * p_y
    d2 = x2 * p_x + y2 * p_y

    # 4. Ladder rung -------------------------------
    ladder_rung_m = (d2 - d1)
    return ladder_rung_m


def haversine(lat1, lon1, lat2, lon2):
    # Devuelve distancia en metros
    import numpy as np
    R = 6371000  # radio de la Tierra en metros
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = phi2 - phi1
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2.0)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2.0)**2
    return 2*R*np.arcsin(np.sqrt(a))

def detectar_balizas_giro(df, umbral_giro=60, min_separacion=40):
    """
    Devuelve una lista de puntos (lat, lon) donde hay un giro brusco en el track.
    - umbral_giro: cambio mínimo de COG para considerar un giro (grados)
    - min_separacion: distancia mínima entre balizas (metros)
    """
    if df.empty or "COG" not in df.columns:
        return []

    balizas = []
    last_idx = None
    cogs = df["COG"].values
    for i in range(1, len(df)):
        delta_cog = abs((cogs[i] - cogs[i-1] + 180) % 360 - 180)
        if delta_cog > umbral_giro:
            lat, lon = df.iloc[i]["Lat"], df.iloc[i]["Lon"]
            # Evitar balizas muy cerca una de otra
            if not balizas or haversine(lat, lon, balizas[-1]["Lat"], balizas[-1]["Lon"]) > min_separacion:
                balizas.append({"Lat": lat, "Lon": lon, "color": [220,20,60], "nombre": f"Baliza {len(balizas)+1}"})
    return balizas

def tramo_tipo_twa(twa_mean):
    if np.isnan(twa_mean):
        return "None"
    abs_twa = abs(twa_mean)
    if abs_twa < 60:
        return "ceñida"
    else:
        return "popa/través"

def detectar_balizas_por_tramos(df, nombre_track="Track1"):
    """
    Analiza el track completo y detecta transiciones ceñida↔popa/través, devolviendo lista de balizas.
    """
    tramo_rows = []
    # Segmentación de tramos por maniobras
    # Asume que ya tienes columnas: 'UTC', 'COG', 'TWA', 'SOG', 'Lat', 'Lon'
    # Aquí, por simplicidad, toma cada punto como posible inicio de tramo si el cambio de COG es grande
    # Mejor si tienes ya las maniobras detectadas (índices). Por ahora, se puede hacer un tramo por cada N puntos o por cada giro
    window = 10  # Ajusta si tienes muchos puntos
    indices = list(range(0, len(df), window))
    if indices[-1] != len(df) - 1:
        indices.append(len(df) - 1)
    for j in range(len(indices) - 1):
        ini = indices[j]
        fin = indices[j+1]
        tramo = df.iloc[ini:fin + 1]
        if tramo.empty:
            continue
        sog_mean = tramo["SOG"].mean()
        cog_mean = tramo["COG"].mean()
        twa_mean = tramo["TWA"].mean() if "TWA" in tramo else np.nan
        tramo_tipo = tramo_tipo_twa(twa_mean)
        utc_ini = tramo["UTC"].iloc[0]
        hora_ini = pd.to_datetime(utc_ini).strftime("%H:%M:%S")
        tramo_rows.append({
            "Track": nombre_track,
            "Hora inicio": hora_ini,
            "TWA prom.": f"{twa_mean:.1f}" if not np.isnan(twa_mean) else "-",
            "Tramo": tramo_tipo,
            "Lat": tramo["Lat"].iloc[0],
            "Lon": tramo["Lon"].iloc[0],
        })
    # Ahora detecta transiciones ceñida↔popa/través
    balizas_tramos = []
    for i in range(1, len(tramo_rows)):
        tipo1 = tramo_rows[i-1]["Tramo"]
        tipo2 = tramo_rows[i]["Tramo"]
        if ((tipo1 == "ceñida" and tipo2 in ["popa", "través"]) or
            (tipo1 in ["popa", "través"] and tipo2 == "ceñida")):
            balizas_tramos.append({
                "Lat": tramo_rows[i]["Lat"],
                "Lon": tramo_rows[i]["Lon"],
                "Track": nombre_track,
                "Tipo": f"{tipo1} → {tipo2}",
                "Hora": tramo_rows[i]["Hora inicio"],
                "color": [220, 20, 60],  # rojo
                "nombre": f"Baliza {len(balizas_tramos)+1}"
            })
    return pd.DataFrame(balizas_tramos)

# --- Intervalos circulares ---
def circular_min_max_deg(series):
    """
    Devuelve (min_circ, max_circ, span) del intervalo circular mínimo que cubre los ángulos.
    series: pandas.Series de ángulos en grados [0,360).
    """
    vals = np.mod(series.dropna().values, 360.0)
    if vals.size == 0:
        return np.nan, np.nan, np.nan
    vals.sort()
    # Brechas entre consecutivos + cierre (último -> primero + 360)
    gaps = np.diff(np.r_[vals, vals[0] + 360.0])
    cut = int(np.argmax(gaps))              # cortar donde la brecha es mayor
    min_circ = vals[(cut + 1) % vals.size]  # inicio del arco corto
    max_circ = vals[cut]                    # fin del arco corto
    span = (max_circ - min_circ) % 360.0
    return min_circ, max_circ, span


