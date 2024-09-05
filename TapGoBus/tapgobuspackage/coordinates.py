from math import radians, degrees, sin, cos, atan2, sqrt
from geopy.geocoders import Nominatim
import gpsd
import asyncio
import logging

from .config import file_params
from .file_opener import open_json

# Configura il logger per ignorare i messaggi di debug
logging.getLogger("gpsd").setLevel(logging.WARNING)
logging.getLogger("geopy").setLevel(logging.WARNING)


# Crea la connessione al gpsd Daemon
async def get_gpsd_connection():
    params = open_json(1, file_params)
    connected = False

    try:
        gpsd.connect()
        connected = True
    except:
        pass

    await asyncio.sleep(params["repetition_wait_seconds"]["default"]) 
    return connected


# Funzione per ottenere e stampare i dati GPS
def get_gps_data():
    params = open_json(1, file_params)
    # Ottenere il pacchetto GPS
    try:
        packet = gpsd.get_current()
        params["position_rt"]["latitude"] = float(packet.lat)
        params["position_rt"]["longitude"] = float(packet.lon)
    except:
        pass

    open_json(0, file_params, params)


# Calcolare la distanza tra due punti geografici
# Formula di Haversine
def calculate_distance(lat1, lon1, lat2, lon2):
    raggio_terra = 6371000  # Raggio medio della Terra in metri
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2]) # Converte da gradi a radianti
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    a = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distanza = raggio_terra * c
    return distanza


# Calcolare coordinate medie tra 2 punti
def calculate_middlepoint(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2]) # Converte da gradi a radianti
    difference_lon = lon2 - lon1
    x = cos(lat2) * cos(difference_lon)
    y = cos(lat2) * sin(difference_lon)

    lat_medio = atan2(sin(lat1) + sin(lat2), ((cos(lat1) + x)**2 + y**2)**0.5)
    lon_medio = lon1 + atan2(y, cos(lat1) + x)

    lat_medio, lon_medio = map(degrees, [lat_medio, lon_medio]) # Converte da radianti a gradi

    return lat_medio, lon_medio


# Ottiene il nome del comune a partire dalle coordinate gps
def get_comune_from_gps(lat, lon):
    geolocator = Nominatim(user_agent="openstreetmap.org")
    location = geolocator.reverse((lat, lon), language='it')
    if location and 'address' in location.raw:
        address = location.raw['address']
        comune = address.get('town') or address.get('city') or address.get('village')
        return comune
    else:
        return None
    
    