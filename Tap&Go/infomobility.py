import xml.etree.ElementTree as ET
import math
import json

############################################################################################
# SEZIONE FILEs
############################################################################################

# Apre il lettura o scrittura i file JSON
def open_json(mode, filename, data=""):
    if mode: # 1 lettura
        with open(filename, "r") as jsonfile:
            data = json.load(jsonfile)
            return data
        
    else: # 0 scrittura
        with open(filename, "w") as jsonfile:
            json.dump(data, jsonfile, indent=4)


############################################################################################
# SEZIONE CALCOLO LINEA
############################################################################################


# Trova il bus corrente e ne memorizza il valore
def calculateLine(file):
    params = open_json(1, file)
    netex = params["netex"]["netex_file_path"] + params["netex"]["netex_file_name"]
    ns = params["netex"]["namespace"]

    journeys = params["infomobility"]["journeys"]
    
    # Carica il file XML
    root = ET.parse(netex)

    # Trova tutte le linee che condividono la stessa tratta parziale a partire dalle fermate trovate
    # Una tratta è tra quelle papabili se include tutte le fermate memorizzate fin ora
    linee_id = []
    for journey in journeys:
         if journey["direction"] == "unbound":
            stops_id = journey["stops"]
    for sjp in root.findall(f".//{ns}ServiceJourneyPattern"):
        stops_sjp = {r.get("ref") for r in sjp.findall(f".//{ns}ScheduledStopPointRef")}
        if set(stops_id) <= set(stops_sjp):
            linee_id.append(sjp.find(f".//{ns}LineRef").get("ref"))
    
    unique_lines_id = list(set(linee_id))
    if len(unique_lines_id) == 1:
        params["infomobility"]["line_id"] = unique_lines_id[0]
        #params["infomobility"]["journeys"] = []
        open_json(0, file, params)

    elif len(unique_lines_id) == 0:
        #params["infomobility"]["journeys"] = []
        open_json(0, file, params)


############################################################################################
# SEZIONE CALCOLO FERMATA
############################################################################################


# Calcolare la distanza tra due punti geografici
# Formula di Haversine
def calculate_distance(lat1, lon1, lat2, lon2):
    raggio_terra = 6371000  # Raggio medio della Terra in metri
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = math.sin(delta_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distanza = raggio_terra * c
    return distanza


# Trova le fermate più vicine al punto di riferimento
def neighborhooded_stops(file):
    params = open_json(1, file)
    netex = params["netex"]["netex_file_path"] + params["netex"]["netex_file_name"]
    ns = params["netex"]["namespace"]

    lat = params["position_rt"]["latitude"]
    lon = params["position_rt"]["longitude"]
    delta = params["position_rt"]["range_meters_approx"]

    # Carica il file XML
    root = ET.parse(netex)

    fermate = root.findall(f".//{ns}ScheduledStopPoint")
    nearby = []
    for fermata in fermate:
        lat_stop = float(fermata.findtext(f".//{ns}Latitude"))
        lon_stop = float(fermata.findtext(f".//{ns}Longitude"))
        distanza = calculate_distance(lat, lon, lat_stop, lon_stop)
        if distanza <= delta:
            nearby.append(fermata.get("id"))
    return nearby


# Funzione per scoprire la fermata al quale il bus si ferma 
def calculateStop(file):
    params = open_json(1, file)

    netex = params["netex"]["netex_file_path"] + params["netex"]["netex_file_name"]
    ns = params["netex"]["namespace"]
    journeys = params["infomobility"]["journeys"]

    # Controlla se nel calcolo fermata precedente si fossero trovate più fermate da verificare
    nearby_stops_id = params["buffer"]["nearby_stops_id"]
    if nearby_stops_id:
        lat = params["position_rt"]["latitude"]
        lon = params["position_rt"]["longitude"]
        next_stops_distance_avg = []
        root = ET.parse(netex)
        
        # Cerca tutte le fermate successive e calcola la distanza media dalla posizione attuale
        # una distanza media minore indica che il verso di percorrenza è quello
        for idx in range(len(nearby_stops_id)):
            distances = []
            for sl in root.findall(f".//{ns}ServiceLink"):
                if sl.find(f"{ns}FromPointRef").get("ref") == nearby_stops_id[idx]:
                    next_stop_id = sl.find(f"{ns}ToPointRef").get("ref")
                    stop = root.find(f".//{ns}ScheduledStopPoint[@id='{next_stop_id}']")
                    lat_stop = float(stop.findtext(f".//{ns}Latitude"))
                    lon_stop = float(stop.findtext(f".//{ns}Longitude"))
                    distances.append(calculate_distance(lat, lon, lat_stop, lon_stop))
            if distances:
                next_stops_distance_avg.append(sum(distances) / len(distances))
            else:
                next_stops_distance_avg.append(-1)
        if min(next_stops_distance_avg) > 0:
            index = next_stops_distance_avg.index(min(next_stops_distance_avg))
            for idx in range(len(journeys)):
                if journeys[idx]["direction"] == "unbound":
                    journeys[idx]["stops"].append(nearby_stops_id[index])
            #params["buffer"]["nearby_stops_id"] = []

    fermate_vicine = neighborhooded_stops(file)

    # Se trova una fermata la si memorizza (sperando sia giusta)
    if len(fermate_vicine) == 1:
        for idx in range(len(journeys)):
            if journeys[idx]["direction"] == "unbound":
                journeys[idx]["stops"].append(fermate_vicine[0])

    # Se trovano più fermate si cerca di capire il verso del bus
    # le prossime coordinate gps ce lo diranno quindi per il momento salviamo in buffer le fermate
    elif len(fermate_vicine) > 1:
        params["buffer"]["nearby_stops_id"] = fermate_vicine

    # Se non si trovano fermate non si può dire niente
    # Se comunque resta il dubbio, non si memorizza nessuna fermata
    
    open_json(0, file, params)


############################################################################################
# SEZIONE VALIDAZIONE TAP
############################################################################################

# Estrai il codice fermata
def estract_stop_id(testo):
    start_trim = testo.rfind(":")
    end_trim = testo.find("_")

    value = testo[start_trim + 1:end_trim]

    return int(value)


# Estrai il codice fermata tariffaria
def estract_tariffzone_id(testo):
    start_trim = testo.rfind(":")

    value = testo[start_trim + 1:]

    return int(value)


# Estrai il codice fermata tariffaria
def estract_line_id(testo):
    start_trim = testo.rfind(":")

    value = testo[start_trim + 1:]

    return value


# Funzione per scoprire le informazioni utili al tap
def calculateValidation(file):
    params = open_json(1, file)
    netex = params["netex"]["netex_file_path"] + params["netex"]["netex_file_name"]
    ns = params["netex"]["namespace"]
    validazioni = params["validazioni"]

    if params["infomobility"]["line_id"] != "" and validazioni: # while
        starting_reference_stop_id = params["validazioni"][0]["last_stop_id"]
        lat = validazioni[0]["latitude"]
        lon = validazioni[0]["longitude"]
        delta = params["position_rt"]["range_meters_approx"]
        line_id = params["infomobility"]["line_id"]

        found = False
        
        root = ET.parse(netex)

        for sjp in root.findall(f".//{ns}ServiceJourneyPattern"):
            if sjp.find(f".//{ns}LineRef").get("ref") == line_id:
                all_linked_stops_id = []
                ref_idx = 0
                for stop in sjp.findall(f".//{ns}ScheduledStopPointRef"):
                    all_linked_stops_id.append(stop.get("ref"))
                for stop_id in all_linked_stops_id:
                    if stop_id == starting_reference_stop_id:
                        ref_idx = all_linked_stops_id.index(stop_id)
                while not found:
                    linked_stops_distance = []
                    buffer_idx = 0
                    for i in range(3):
                        if ref_idx+i >= len(all_linked_stops_id):
                            stop = root.find(f".//{ns}ScheduledStopPoint[@id='{all_linked_stops_id[buffer_idx]}']")
                            lat_stop = float(stop.findtext(f".//{ns}Latitude"))
                            lon_stop = float(stop.findtext(f".//{ns}Longitude"))
                            distance = calculate_distance(lat, lon, lat_stop, lon_stop)
                            if distance <= delta:
                                tariff_zone_id = stop.find(f".//{ns}TariffZoneRef").get("ref")
                                params["validazioni"][0]["fermata"] = estract_stop_id(all_linked_stops_id[buffer_idx])
                                params["validazioni"][0]["codice fermata_tariffaria"] = estract_tariffzone_id(tariff_zone_id)
                                found = True 
                            else:
                                linked_stops_distance.append(distance)
                            buffer_idx += 1
                        else:
                            stop = root.find(f".//{ns}ScheduledStopPoint[@id='{all_linked_stops_id[ref_idx+i]}']")
                            lat_stop = float(stop.findtext(f".//{ns}Latitude"))
                            lon_stop = float(stop.findtext(f".//{ns}Longitude"))
                            distance = calculate_distance(lat, lon, lat_stop, lon_stop)
                            if distance <= delta:
                                tariff_zone_id = stop.find(f".//{ns}TariffZoneRef").get("ref")
                                params["validazioni"][0]["fermata"] = estract_stop_id(all_linked_stops_id[ref_idx+i])
                                params["validazioni"][0]["codice fermata_tariffaria"] = estract_tariffzone_id(tariff_zone_id)
                                found = True 
                                break
                            else:
                                linked_stops_distance.append(distance)
                    if found:
                        break
                    #print(linked_stops_distance)
                    if max(linked_stops_distance) == linked_stops_distance[2]:
                        for link in root.findall(f".//{ns}ServiceLink"):
                            if link.find(f"{ns}FromPointRef").get("ref") == all_linked_stops_id[ref_idx] and link.find(f"{ns}FromPointRef").get("ref") == all_linked_stops_id[ref_idx+1]:
                                if validazioni["operazione"] == "check-in":
                                    stop = root.find(f".//{ns}ScheduledStopPoint[@id='{all_linked_stops_id[ref_idx]}']")
                                    tariff_zone_id = stop.find(f".//{ns}TariffZoneRef").get("ref")
                                    params["validazioni"][0]["fermata"] = estract_stop_id(all_linked_stops_id[ref_idx])
                                    params["validazioni"][0]["codice fermata_tariffaria"] = estract_tariffzone_id(tariff_zone_id)
                                    found = True 
                                elif validazioni["operazione"] == "check-out":
                                    if ref_idx+1 >= len(all_linked_stops_id):
                                        stop = root.find(f".//{ns}ScheduledStopPoint[@id='{all_linked_stops_id[0]}']")
                                        params["validazioni"][0]["fermata"] = estract_stop_id(all_linked_stops_id[0])
                                    else:
                                        stop = root.find(f".//{ns}ScheduledStopPoint[@id='{all_linked_stops_id[ref_idx+1]}']")
                                        params["validazioni"][0]["fermata"] = estract_stop_id(all_linked_stops_id[ref_idx+1])
                                    tariff_zone_id = stop.find(f".//{ns}TariffZoneRef").get("ref")
                                    params["validazioni"][0]["codice fermata_tariffaria"] = estract_tariffzone_id(tariff_zone_id)
                                    found = True 
                    elif max(linked_stops_distance) == linked_stops_distance[0]:
                        if ref_idx+1 >= len(all_linked_stops_id):
                            ref_idx = 0
                        else:
                            ref_idx += 1

    params["validazioni"][0]["codice_linea"] = estract_line_id(line_id)
    #params["validazioni"][0] = []
    open_json(0, file, params)


############################################################################################
# SEZIONE INFOMOBILITà ADMIN
############################################################################################


# FUNZIONE LEGACY !!!!
def getInfomobility(file):
    params = open_json(1, file)
    netex = params["netex"]["netex_file_path"] + params["netex"]["netex_file_name"]
    ns = params["netex"]["namespace"]

    journeys = params["infomobility"]["journeys"]
    line_id = params["infomobility"]["line_id"]
    
    # Carica il file XML
    root = ET.parse(netex)

    #Se è in memoria la linea, elimina le tratte trovate fin ora e aggiungi tutte
    if line_id:
        journeys = []

        for sjp in root.findall(f".//{ns}ServiceJourneyPattern"):
            journey = sjp.find(f".//{ns}LineRef[@ref='" + line_id + "']")
            if journey:
                journey_id = sjp.get("id")
                direction = sjp.findtext(f"{ns}DirectionType")

                # Trova le fermate per ciascuna tratta
                stops = []
                for ssp in sjp.findall(f".//{ns}ScheduledStopPointRef"):
                    stop_id = ssp.get("ref")
                    stop = root.find(f".//{ns}ScheduledStopPoint[@id='" + stop_id + "']")
                    stop_name = stop.findtext(f"{ns}Description")
                    stops.append({"id": stop_id, "name": stop_name})

                journeys.append({
                    "id": journey_id,
                    "direction": direction,
                    "stops": stops
                })

    open_json(0, file, params)


