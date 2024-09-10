import asyncio
import random
import logging

from .config import file_params
from .file_opener import open_json

logger = logging.getLogger(" ")


# Simula le tratte di una linea e i sui valori gps
async def simulate(file):
    while True:
        params = open_json(1, file_params)
        infos = open_json(1, file)

        stops, idx = [], -1
        for j in infos["journeys"]:
            for s in j["stops"]:
                stops.append(s)
        for index in range(len(stops)):
            if params["position_rt"]["latitude"]==stops[index]["latitude"] and params["position_rt"]["longitude"]==stops[index]["longitude"]:
                idx = index
                break

        if random.random() < 0.75:
            probability = random.random()
            if probability < 0.4:
                idx = idx + 1
            elif probability < 0.9: 
                idx = (idx + random.randint(1, 3)) % len(stops)
            elif probability < 0.98:
                idx = (idx + random.randint(4, 5)) % len(stops)
            else:
                idx = (idx + random.randint(1, len(stops)-1)) % len(stops)
        else:
            if idx == -1:
                idx = 0

        params["position_rt"]["latitude"] = stops[idx]["latitude"]
        params["position_rt"]["longitude"] = stops[idx]["longitude"]
        logger.info("In simulazione le coordinate della fermata con codice: " + stops[idx]["Code"])
        open_json(0, file_params, params)
        await asyncio.sleep(params["repetition_wait_seconds"]["calculate_stops"]-5) 


# Simula delle coordinate gps tra 2 fermate conseguenziali
def sim_gps_tap(ref_stop_id, file):
    infos = open_json(1, file)

    stops = []
    for j in infos["journeys"]:
        for s in j["stops"]:
            stops.append(s)
    for index in range(len(stops)):
        if stops[index]["id"] == ref_stop_id:
            idx = index
            break
    ref_lat = stops[idx]["latitude"]
    ref_lon = stops[idx]["longitude"]
    next_lat = stops[idx+1]["latitude"]
    next_lon = stops[idx+1]["longitude"]
    
    u = random.random()
    lat = ref_lat + u * (next_lat - ref_lat)
    lon = ref_lon + u * (next_lon - ref_lon)

    return lat, lon

