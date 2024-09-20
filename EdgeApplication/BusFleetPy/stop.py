from datetime import datetime
from math import exp, log
import asyncio
import logging

from .config import file_params, file_buffer
from .file_opener import open_json
from .parser import search_all, search_elem, search_by_ref, search_by_id, get_root
from .coordinates import get_gps_data, calculate_distance

# Creazione di un logger specifico per questo modulo con nome personalizzato
logger = logging.getLogger("[ STOP ]")


# Calcola il tempo di attesa per di riattivare calculateStops
def optimize_asleep():
    params = open_json(1, file_params)
    asleep_default = params["await_seconds"]["default"]
    asleep_stops = params["await_seconds"]["calculate_stops"]
    asleep_line = params["await_seconds"]["calculate_line"]
    asleep_until_default = params["time_until_await_default"]
    buffer = open_json(1, file_buffer)
    last_stop_time = datetime.strptime(buffer["journey"]["last_stop_time"], "%Y-%m-%d %H:%M:%S")
    current_time = datetime.now()

    difference_time = current_time - last_stop_time
    m = (1 - asleep_stops) / (asleep_until_default - 0)
    q = asleep_stops

    # Se non trova una fermata entro un ciclo di calculateLine, diminuisci linearmente
    if difference_time.seconds <= asleep_line:
        asleep = m * difference_time.seconds + q
    # Dal secondo ciclo di calculateLine diminuisci esponenzialmente
    elif asleep_line < difference_time.seconds < asleep_until_default:
        a = m * asleep_line + q
        k = log(1 / a) / (asleep_until_default - asleep_line)
        asleep = a * exp(k * (difference_time.seconds - asleep_line))
    # mantiene infine come valore di attesa minimo quello di default
    elif difference_time.seconds >= asleep_until_default:
        asleep = asleep_default
    return asleep


# Trova il codice della fermata legata alle info gps
def calculate_stops():
    buffer = open_json(1, file_buffer)
    params = open_json(1, file_params)
    stops = []
    lat = buffer["position_rt"]["latitude"]
    lon = buffer["position_rt"]["longitude"]

    # Controlla se nel calcolo fermata precedente sono state trovate più fermate
    nearby_stops_id = buffer["nearby_stops_id"]
    if nearby_stops_id:
        # Cerca tutte le fermate successive e calcola la distanza media dalla posizione attuale
        # una distanza media minore indica che il verso di percorrenza è quello
        next_stops_distance_avg = []
        for idx in range(len(nearby_stops_id)):
            distances = []
            for link in search_by_ref(get_root(), "ServiceLink", "FromPointRef", nearby_stops_id[idx]):
                next_stop_id = search_elem(link, "ToPointRef", "ref")
                stop = search_by_id(get_root(), "ScheduledStopPoint", next_stop_id)
                lat_stop = float(search_elem(stop, "Latitude", "text"))
                lon_stop = float(search_elem(stop, "Longitude", "text"))
                distances.append(calculate_distance(lat, lon, lat_stop, lon_stop))
            if distances:
                next_stops_distance_avg.append(sum(distances) / len(distances))
            else:
                next_stops_distance_avg.append(-1)
        if min(next_stops_distance_avg) > 0:
            index = next_stops_distance_avg.index(min(next_stops_distance_avg))
            stops.append(nearby_stops_id[index])

    # Trova le fermate più vicine al punto di riferimento
    delta = params["interception_radius_gps_meters"]
    nearby = []
    for stop in search_all(get_root(), "ScheduledStopPoint"):
        lat_stop = float(search_elem(stop, "Latitude", "text"))
        lon_stop = float(search_elem(stop, "Longitude", "text"))
        distance = calculate_distance(lat, lon, lat_stop, lon_stop)
        if distance <= delta:
            nearby.append(stop.get("id"))

    # Se trova una fermata la si memorizza
    if len(nearby) == 1:
        stops.append(nearby[0])

    # Se trovano più fermate si cerca di capire il verso del bus
    # le prossime coordinate gps ce lo diranno quindi per il momento salviamo in buffer le fermate
    elif len(nearby) > 1:
        buffer["nearby_stops_id"] = nearby
        open_json(0, file_buffer, buffer)
            
    return stops


async def calculateStops():
    while True:
        buffer = open_json(1, file_buffer)
        buffer_stops = buffer["journey"]["stops"]
        found = False
        get_gps_data()
        stops = calculate_stops()
        if stops:
            if buffer_stops:
                if buffer_stops[-1] != stops[0]:
                    found = True
            else:
                found = True
            
        if found:
            logger.info("I codici delle fermate sono: %s", ', '.join(stops))
            buffer["journey"]["last_stop_time"] = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            for idx in range(len(stops)):
                buffer["journey"]["stops"].append(stops[idx])
        else:
            logger.info("Nessuna fermata trovata.")
        open_json(0, file_buffer, buffer)

        asleep_stops = optimize_asleep()
        await asyncio.sleep(asleep_stops) # Attende prima di riattivarsi


