import asyncio
import random
import logging

from .config import file_params, file_buffer
from .file_opener import open_json

logger = logging.getLogger(" ")


# Ritorna il nome della linea usata per la simulazione
async def get_sim():
    params = open_json(1, file_params)
    return params["simulator_file"]["name_line"]
    await asyncio.sleep(params["await_seconds"]["default"]) 


# Simula le tratte di una linea e i sui valori gps
async def simulate():
    while True:
        params = open_json(1, file_params)
        sim_file = params["simulator_file"]["path"] + "infomobility-" + params["simulator_file"]["name_line"] + ".json"
        try:
            infos = open_json(1, sim_file)
        except:
            print("Linea da simulare non presente nel database.")
            print("Per favore, creala richiamando il programma opportuno oppure cambia la linea.")
            exit()
        buffer = open_json(1, file_buffer)
        lat = buffer["position_rt"]["latitude"]
        lon = buffer["position_rt"]["longitude"]

        stops, idx = [], -1
        for j in infos["journeys"]:
            for s in j["stops"]:
                stops.append(s)
        for index in range(len(stops)):
            if lat == stops[index]["latitude"] and lon == stops[index]["longitude"]:
                idx = index
                break

        if random.random() < 0.75:
            probability = random.random()
            if probability < 0.4:
                idx = idx + 1
            elif probability < 0.75: 
                idx = (idx + random.randint(1, 2)) % len(stops)
            elif probability < 0.98:
                idx = (idx + random.randint(1, 3)) % len(stops)
            elif probability > 0.98:
                idx = (idx + random.randint(4, 5)) % len(stops)
        else:
            if idx == -1:
                idx = 0

        buffer["position_rt"]["latitude"] = stops[idx]["latitude"]
        buffer["position_rt"]["longitude"] = stops[idx]["longitude"]
        logger.info("In simulazione le coordinate della fermata "+ stops[idx]["Name"] + " con codice: " + stops[idx]["Code"])
        open_json(0, file_buffer, buffer)

        await asyncio.sleep(params["await_seconds"]["calculate_stops"]-5) 


# Simula delle coordinate gps tra 2 fermate conseguenziali
def sim_gps_tap(ref_stop_id, file):
    try:
        infos = open_json(1, file)
    except:
        print("Linea da simulare non presente nel database.")
        print("Per favore, creala richiamando il programma opportuno oppure cambia la linea.")
        exit()

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

