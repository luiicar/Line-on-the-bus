from datetime import datetime
import json
import asyncio
import logging

from .config import file_params, file_buffer
from .file_opener import open_json
from .parser import search_all, search_elem, search_by_ref, search_by_id, get_root, get_code_svr
from .coordinates import calculate_distance, calculate_middlepoint, get_comune_from_gps

# Creazione di un logger specifico per questo modulo con nome personalizzato
logger = logging.getLogger("[ VALIDATION ]")


# Simula l'esperienza di un cliente capendo la direzione corretta da considerare
def experience(linked_stops, validation, journey, stop, terminus):
    params = open_json(1, file_params)

    # Calcola il tempo medio dalla fermata di riferimento al capolinea
    # Considera solo i ServiceJourney della tratta di riferimento di quella fascia oraria
    time_range = params["time_slot_minutes"]
    last_stop_date_str = validation["__added__"]["last_stop_time"]
    start_trim = last_stop_date_str.rfind(" ")
    last_stop_time_str = last_stop_date_str[start_trim + 1:]
    last_stop_time = datetime.strptime(last_stop_time_str, "%H:%M:%S")
    difference_times = []
    
    for service_journey in search_by_ref(get_root(), "ServiceJourney", "ServiceJourneyPatternRef", journey):
        for timetable_r in search_by_ref(service_journey, "TimetabledPassingTime", "StopPointInJourneyPatternRef", stop):
            stop_sj_time = datetime.strptime(search_elem(timetable_r, "DepartureTime", "text"), "%H:%M:%S")
            difference = (abs(stop_sj_time - last_stop_time).total_seconds() % 3600) // 60 
            if difference < time_range:
                for timetable_t in search_by_ref(service_journey, "TimetabledPassingTime", "StopPointInJourneyPatternRef", terminus):
                    terminus_sj_time = datetime.strptime(search_elem(timetable_t, "DepartureTime", "text"), "%H:%M:%S")
                    stop_to_terminus_difference = (terminus_sj_time - stop_sj_time).total_seconds() % 3600 // 60
                    difference_times.append(stop_to_terminus_difference)
    time_stop_to_terminus_avg = sum(difference_times) / len(difference_times) 

    
    # Capire qual'è la tratta di riferimento per il calcolo della validazione
    # Se l'orario della validazione è minore del tempo medio per arrivare al capolinea, la tratta è quella, altrimenti è l'altra
    validation_date_str = validation["data_validazione"]
    start_trim = validation_date_str.rfind(" ")
    validation_time_str = validation_date_str[start_trim + 1:]
    validation_date_time = datetime.strptime(validation_time_str, "%H:%M:%S")
    
    last_stop_time = last_stop_time.hour * 60 + last_stop_time.minute
    validation_date_time = validation_date_time.hour * 60 + validation_date_time.minute
        
    if last_stop_time + time_stop_to_terminus_avg < validation_date_time:
        for item in linked_stops:
            if item["id"] != journey:
                ref_linked = item["stops"]  
    else:
        for item in linked_stops:
            if item["id"] == journey:
                ref_linked = item["stops"] 
    return ref_linked


# Trova i valori della fermata fisica e tariffaria legati al tap
def calculate_validation(validation):
    buffer = open_json(1, file_buffer)
    èarams = open_json(1, file_params)
    
    # Creazione delle liste di link per ogni tratta e definizione riferimenti
    line_id = buffer["line_id"]
    reference_stop_id = validation["__added__"]["last_stop_id"]
    linked_stops = []
    found = False

    for journey in search_by_ref(get_root(), "ServiceJourneyPattern", "LineRef", line_id):
        linked_stops. append({
            "id": journey.get("id"),
            "stops": search_all(journey, "ScheduledStopPointRef/@ref")
        })

        items = search_by_ref(journey, "StopPointInJourneyPattern", "ScheduledStopPointRef", reference_stop_id)
        if items:
            reference_journey_id = journey.get("id") # Riferimento tratta
            stop_in_journey = items[-1]
            reference_journey_stop_id = stop_in_journey.get("id") # Riferimento fermata
            journey_terminus = search_elem(journey, "StopPointInJourneyPattern", "last")
            reference_journey_terminus_id = journey_terminus.get("id") # Riferimento capolinea
            
    ref_linked = experience(linked_stops, validation, reference_journey_id, reference_journey_stop_id, reference_journey_terminus_id)

    # Calcolo link e fermata legata al tap
    lat = validation["__added__"]["latitude"]
    lon = validation["__added__"]["longitude"]
    delta = params["interception_radius_gps_meters"]
    link_distance = []
    found = False

    for idx in range(len(ref_linked)):
        stop = search_by_id(get_root(), "ScheduledStopPoint", ref_linked[idx])
        lat_stop = float(search_elem(stop, "Latitude", "text"))
        lon_stop = float(search_elem(stop, "Longitude", "text"))
        distance = calculate_distance(lat, lon, lat_stop, lon_stop)
        if distance <= delta:
            found = True
            break
        else:
            if idx == 0:
                stop_gps = {"lat": lat_stop, "lon": lon_stop}
            else:
                lat_middle, lon_middle = calculate_middlepoint(stop_gps["lat"], stop_gps["lon"], lat_stop, lon_stop)
                distance = calculate_distance(lat, lon, lat_middle, lon_middle)
                link_distance.append(distance)
                stop_gps = {"lat": lat_stop, "lon": lon_stop}
    if not found:
        if validation["operazione"] == "check-in":
            idx = link_distance.index(min(link_distance))
        elif validation["operazione"] == "check-out":
            idx = link_distance.index(min(link_distance)) + 1
        stop = search_by_id(get_root(), "ScheduledStopPoint", ref_linked[idx])

    # Calcolo fermata fisica
    fermata_fisica = int(search_elem(stop, "PublicCode", "text") or 0000)
    # Calcolo fermata tariffaria
    tariff_zone_id = search_elem(stop, "TariffZoneRef", "ref")
    tariff_zone = search_by_id(get_root(), "TariffZone", tariff_zone_id)
    fermata_tariffaria = int(search_elem(tariff_zone, "Name", "text") or 000)
    if fermata_tariffaria == 000:
        comune = get_comune_from_gps(lat, lon)
        fermata_tariffaria = get_code_svr(comune)
    # Calcolo linea
    line = search_by_id(get_root(), "Line", line_id)
    linea = search_elem(line, "Name", "text")
    return fermata_fisica, fermata_tariffaria, linea
    

async def calculateValidations():
    while True:
        buffer = open_json(1, file_buffer)
        validazioni = buffer["validazioni"]
        line_id = buffer["line_id"]

        if line_id == "":
            pass
        elif not validazioni:
            pass

        elif buffer["line_id"] != "" and validazioni:
            fermata_fisica, fermata_tariffaria, linea = calculate_validation(validazioni[0])
            buffer["validazioni"][0]["fermata"] = fermata_fisica
            buffer["validazioni"][0]["codice_fermata_tariffaria"] = fermata_tariffaria
            buffer["validazioni"][0]["codice_linea"] = linea
            buffer["validazioni"][0].pop("__added__")
            logger.info("Validazione in output!")
            logger.info("%s", json.dumps(buffer["validazioni"][0]))
            buffer["validazioni"].pop(0)
            open_json(0, file_buffer, buffer)
        
        params = open_json(1, file_params)
        await asyncio.sleep(params["await_seconds"]["default"])  
