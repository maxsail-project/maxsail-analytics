# utils.py
import math
import pandas as pd
import gpxpy
import pyproj
import numpy as np

wgs84 = pyproj.Geod(ellps="WGS84")

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
    """Convierte un archivo GPX en un DataFrame normalizado para el visor."""
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
                if prev_point is None:
                    prev_point = point
                    continue
                lat, lon = point.latitude, point.longitude
                distance, COG, _ = calculate_distance_bearing(prev_point.latitude, prev_point.longitude, lat, lon)
                time_diff = (point.time - prev_point.time).total_seconds()
                SOG = calculate_velocity(prev_point.latitude, prev_point.longitude, lat, lon, time_diff)
                TWA = estimate_twa(COG, TWD)
                VMG = calculate_vmg(SOG, TWA)
                prev_point = point
                if SOG < 0.9:
                    continue
                UTC = point.time
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
    df = pd.DataFrame(rows)
    if not df.empty and 'UTC' in df.columns:
        df['UTC'] = pd.to_datetime(df['UTC']).dt.tz_localize(None)
    return df


def distance_on_ladder(lat1, lon1, lat2, lon2, twd_deg):
    """
    Devuelve la distancia (en metros) entre dos puntos, medida sobre el eje perpendicular al TWD.
    El signo indica qué punto está a barlovento.
    """
    # Referencia local para el cálculo: lat1, lon1
    R = 6371000  # radio Tierra en metros
    # Convertir a desplazamiento local en metros
    dlat2 = np.radians(lat2 - lat1)
    dlon2 = np.radians(lon2 - lon1)
    xm2 = R * dlon2 * np.cos(np.radians((lat1 + lat2)/2))
    ym2 = R * dlat2

    # Azimut del peldaño (perpendicular al viento)
    az_peld = np.radians((twd_deg + 90) % 360)
    # Vector unitario del peldaño
    ux, uy = np.cos(az_peld), np.sin(az_peld)
    # Proyección sobre ese eje (track 2 menos track 1)
    dist_peld = xm2 * ux + ym2 * uy
    #return dist_peld  # metros (positivo: track 2 a barlovento de track 1)
    return distance_on_axis(lat1, lon1, lat2, lon2, (twd_deg + 90) % 360)

def distance_on_axis(lat1, lon1, lat2, lon2, axis_deg):
    """
    Distancia entre dos puntos, proyectada sobre el eje con rumbo axis_deg (en grados, desde el norte).
    Devuelve la diferencia en metros (track2 - track1).
    """
    R = 6371000
    dlat2 = np.radians(lat2 - lat1)
    dlon2 = np.radians(lon2 - lon1)
    xm2 = R * dlon2 * np.cos(np.radians((lat1 + lat2)/2))
    ym2 = R * dlat2

    az_axis = np.radians(axis_deg % 360)
    ux, uy = np.cos(az_axis), np.sin(az_axis)
    proj2 = xm2 * ux + ym2 * uy  # punto 2 respecto a punto 1
    return proj2  # metros (positivo: track2 más adelante sobre el eje)
