from datetime import datetime
import asyncio
import logging

from .config import file_params
from .file_opener import open_json
from .parser import search_all, search_elem, search_by_ref, search_by_id, get_root
from .coordinates import get_gps_data, calculate_distance

# Creazione di un logger specifico per questo modulo con nome personalizzato
logger = logging.getLogger("[ STOP ]")


# Trova il codice della fermata legata alle info gps
def calculate_stops():
    params = open_json(1, file_params)
    stops = []
    lat = params["position_rt"]["latitude"]
    lon = params["position_rt"]["longitude"]

    # Controlla se nel calcolo fermata precedente sono state trovate più fermate
    nearby_stops_id = params["buffer"]["nearby_stops_id"]
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
    delta = params["position_rt"]["range_meters_approx"]
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
        params["buffer"]["nearby_stops_id"] = nearby
        open_json(0, file_params, params)
            
    return stops


async def calculateStops():
    while True:
        params = open_json(1, file_params)
        asleep_line = params["repetition_wait_seconds"]["calculate_line"]
        asleep_stops = params["repetition_wait_seconds"]["calculate_stops"]
        found = False
        get_gps_data()
        stops = calculate_stops()
        if stops:
            if params["infomobility"]["journey"]["stops"]:
                if params["infomobility"]["journey"]["stops"][-1] != stops[0]:
                    found = True
            else:
                found = True
            
        if found:
            logger.info("I codici delle fermate sono: %s", ', '.join(stops))
            params["buffer"]["count_divide"] = 1
            params["infomobility"]["journey"]["last_stop_time"] = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            for idx in range(len(stops)):
                params["infomobility"]["journey"]["stops"].append(stops[idx])
        else:
            logger.info("Nessuna fermata trovata.")

        current_time = datetime.now()
        last_stop_time = datetime.strptime(params["infomobility"]["journey"]["last_stop_time"], "%Y-%m-%d %H:%M:%S")
        difference_time = current_time - last_stop_time
        if difference_time.total_seconds() > asleep_line and asleep_stops > asleep_stops/10:
            asleep_stops = asleep_stops/(params["buffer"]["count_divide"]*2)
            params["buffer"]["count_divide"] += 1
        open_json(0, file_params, params)
        await asyncio.sleep(asleep_stops) # Attende prima di riattivarsi


