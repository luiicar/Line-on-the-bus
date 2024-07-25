#import xml.etree.ElementTree as ET
from lxml import etree
from datetime import datetime
import math
import json

file = "params.json" 

with open(file, "r") as jsonfile:
    params = json.load(jsonfile)
netex = params["netex"]["netex_file_path"] + params["netex"]["netex_file_name"]
ns = {'ns': params["netex"]["namespace"]}
root = etree.parse(netex) # Carica il file XML

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
def calculateLine():
    params = open_json(1, file)
    journeys = params["infomobility"]["journeys"]

    # Trova tutte le linee che condividono la stessa tratta parziale a partire dalle fermate trovate
    # Una tratta è tra quelle papabili se include tutte le fermate memorizzate fin ora
    lines_id = []
    for journey in journeys:
         if journey["direction"] == "unbound":
            stops_id = journey["stops"]
    for sjp in root.xpath(".//ns:ServiceJourneyPattern", namespaces=ns):
        stops_sjp = {r.get("ref") for r in sjp.xpath(".//ns:ScheduledStopPointRef", namespaces=ns)}
        if set(stops_id) <= set(stops_sjp):
            lines_id.append(sjp.xpath(".//ns:LineRef/@ref", namespaces=ns)[0])
    
    # Se nella lista ci sta una sola linea, allora l'abbiamo trovata
    if len(lines_id) == 1:
        params["infomobility"]["line_id"] = lines_id[0]       
        #params["infomobility"]["journeys"] = [] 

    # Se la lista è vuota vuol dire che abbiamo catturato delle fermate sbagliate
    # conviene ricominciare la ricerca
    elif len(lines_id) == 0:
        params["infomobility"]["line_id"] = []
        params["infomobility"]["journeys"] = []
        params["infomobility"]["journeys"].append({
            "id": "",
            "direction": "unbound",
            "timestamp": "",
            "stops": []
        })
    
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
def neighborhooded_stops():
    params = open_json(1, file)
    lat = params["position_rt"]["latitude"]
    lon = params["position_rt"]["longitude"]
    delta = params["position_rt"]["range_meters_approx"]

    nearby = []
    for stop in root.xpath(".//ns:ScheduledStopPoint", namespaces=ns):
        lat_stop = float(stop.xpath(".//ns:Latitude/text()", namespaces=ns)[0])
        lon_stop = float(stop.xpath(".//ns:Longitude/text()", namespaces=ns)[0])
        distance = calculate_distance(lat, lon, lat_stop, lon_stop)
        if distance <= delta:
            nearby.append(stop.get("id"))
    return nearby


# Funzione per scoprire la fermata al quale il bus si ferma 
def calculateStop():
    params = open_json(1, file)
    journeys = params["infomobility"]["journeys"]

    # Controlla se nel calcolo fermata precedente sono state trovate più fermate
    nearby_stops_id = params["buffer"]["nearby_stops_id"]
    if nearby_stops_id:
        lat = params["position_rt"]["latitude"]
        lon = params["position_rt"]["longitude"]
        
        # Cerca tutte le fermate successive e calcola la distanza media dalla posizione attuale
        # una distanza media minore indica che il verso di percorrenza è quello
        next_stops_distance_avg = []
        for idx in range(len(nearby_stops_id)):
            distances = []
            for sl in root.xpath(f".//ns:ServiceLink", namespaces=ns):
                if sl.xpath(f"ns:FromPointRef/@ref", namespaces=ns)[0] == nearby_stops_id[idx]:
                    next_stop_id = sl.xpath("ns:ToPointRef/@ref", namespaces=ns)[0]
                    stop = root.find(f".//ns:ScheduledStopPoint[@id='{next_stop_id}']", namespaces=ns)
                    lat_stop = float(stop.xpath(".//ns:Latitude/text()", namespaces=ns)[0])
                    lon_stop = float(stop.xpath(".//ns:Longitude/text()", namespaces=ns)[0])
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

    fermate_vicine = neighborhooded_stops()

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
def calculateValidation():
    params = open_json(1, file)
    validazioni = params["validazioni"]

    if params["infomobility"]["line_id"] != "" and validazioni: # while
        # Step 1
        line_id = params["infomobility"]["line_id"]
        ref_stop_id = params["validazioni"][0]["last_stop_id"]
        
        linked_stops_id = []
        for sjp in root.xpath(".//ns:ServiceJourneyPattern", namespaces=ns):
            # Creazione delle liste di link per ogni tratta
            if sjp.xpath(".//ns:LineRef/@ref", namespaces=ns)[0] == line_id:
                linked_stops_id. append({
                    "id": sjp.xpath(".//ns:ServiceJourneyPattern/@id", namespaces=ns)[0],
                    "stops": sjp.xpath(".//ns:ScheduledStopPointRef/@ref", namespaces=ns)
                })
                # Conversione codice ScheduledStopPoint a codice StopPointInJourneyPattern  
                for spinjp in sjp.xpath(".//ns:StopPointInJourneyPattern", namespaces=ns):
                    if spinjp.xpath(".//ns:ScheduledStopPointRef/@ref", namespaces=ns)[0] == ref_stop_id:
                        ref_journey_id = sjp.xpath(".//ns:ServiceJourneyPattern/@id", namespaces=ns)[0]
                        journey_stop_id = spinjp.xpath(".//ns:StopPointInJourneyPattern/@id", namespaces=ns)[0]
                        
        
        # Step 2
        time_range = params["time_min_approx"]
        valid_stop_time = datetime.strptime(params["validazioni"][0]["last_stop_time"], "%H:%M:%S")
        difference_times = []
        # Calcola il tempo medio dalla fermata di riferimento al capolinea
        # Considera solo i ServiceJourney della tratta di riferimento di quella fascia oraria
        for sj in root.xpath(".//ns:ServiceJourney", namespaces=ns):
            if sj.xpath(".//ns:ServiceJourneyPatternRef/@ref", namespaces=ns)[0] == ref_journey_id:
                stop_in_sj = sj.find(f".//ns:StopPointInJourneyPattern[@ref='{journey_stop_id}']", namespaces=ns)
                stop_sj_time_str = stop_in_sj.xpath(".//ns:DepartureTime/text()", namespaces=ns)[0]
                stop_sj_time = datetime.strptime(stop_sj_time_str, "%H:%M:%S")
                difference = abs(stop_sj_time - valid_stop_time)
                difference_min = (difference.seconds % 3600) // 60
                if difference_min < time_range:
                    stop_in_sj = sj.xpath(".//ns:StopPointInJourneyPattern/last()", namespaces=ns)[0]
                    terminus_time_sj_str = stop_in_sj.xpath(".//ns:DepartureTime/text()", namespaces=ns)[0]
                    terminus_sj_time = datetime.strptime(terminus_time_sj_str, "%H:%M:%S")
                    difference = terminus_sj_time - stop_sj_time
                    difference_times.append(difference)
        difference_avg = sum(difference_times) / len(difference_times) 

        # Step 3
        # Capire qual'è la tratta di riferimento per il calcolo della validazione
        # Se l'orario della validazione è maggiore del tempo medio per arrivare al capolinea, la tratta è quella, altrimenti è l'altra
        valid_date_str = params["validazioni"][0]["data_validazione"]
        start_trim = valid_date_str.rfind(" ")
        valid_time_str = valid_date_str[start_trim + 1:]
        valid_date_time = datetime.strptime(valid_time_str, "%H:%M:%S")
        
        ref_idx = 0
        if stop_sj_time + difference_avg > valid_date_time:
            for item in linked_stops_id:
                if item["id"] != ref_journey_id:
                    ref_linked = item["stops"]  
        else:
            for item in linked_stops_id:
                if item["id"] == ref_journey_id:
                    ref_linked = item["stops"]  
            for stop_id in ref_linked:
                if stop_id == ref_stop_id:
                    ref_idx = linked_stops_id.index(stop_id)

        # Step 4
        # Calcolo link e fermata legata al tap
        lat = validazioni[0]["latitude"]
        lon = validazioni[0]["longitude"]
        delta = params["position_rt"]["range_meters_approx"]
        found = False
        while not found:
            linked_stops_distance = []
            for i in range(3):
                stop = root.find(f".//{ns}ScheduledStopPoint[@id='{ref_linked[ref_idx+i]}']")
                lat_stop = float(stop.findtext(f".//{ns}Latitude"))
                lon_stop = float(stop.findtext(f".//{ns}Longitude"))
                distance = calculate_distance(lat, lon, lat_stop, lon_stop)
                if distance <= delta:
                    tariff_zone_id = stop.find(f".//{ns}TariffZoneRef").get("ref")
                    params["validazioni"][0]["fermata"] = estract_stop_id(ref_linked[ref_idx+i])
                    params["validazioni"][0]["codice fermata_tariffaria"] = estract_tariffzone_id(tariff_zone_id)
                    found = True 
                    break
                else:
                    linked_stops_distance.append(distance)
            if found:
                break
            if max(linked_stops_distance) == linked_stops_distance[2]:
                for link in root.findall(f".//{ns}ServiceLink"):
                    if link.find(f"{ns}FromPointRef").get("ref") == ref_linked[ref_idx] and link.find(f"{ns}FromPointRef").get("ref") == linked_stops_id[ref_idx+1]:
                        if validazioni["operazione"] == "check-in":
                            stop = root.find(f".//{ns}ScheduledStopPoint[@id='{linked_stops_id[ref_idx]}']")
                            tariff_zone_id = stop.find(f".//{ns}TariffZoneRef").get("ref")
                            params["validazioni"][0]["fermata"] = estract_stop_id(linked_stops_id[ref_idx])
                            params["validazioni"][0]["codice fermata_tariffaria"] = estract_tariffzone_id(tariff_zone_id)
                            found = True 
                        elif validazioni["operazione"] == "check-out":
                            stop = root.find(f".//{ns}ScheduledStopPoint[@id='{linked_stops_id[ref_idx+1]}']")
                            params["validazioni"][0]["fermata"] = estract_stop_id(linked_stops_id[ref_idx+1])
                            tariff_zone_id = stop.find(f".//{ns}TariffZoneRef").get("ref")
                            params["validazioni"][0]["codice fermata_tariffaria"] = estract_tariffzone_id(tariff_zone_id)
                            found = True 
            elif max(linked_stops_distance) == linked_stops_distance[0]:
                if ref_idx+1 >= len(linked_stops_id):
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
def getInfomobilityBackdoor():
    params = open_json(1, file)
    netex = params["netex"]["netex_file_path"] + params["netex"]["netex_file_name"]
    ns = params["netex"]["namespace"]

    journeys = params["infomobility"]["journeys"]
    line_id = params["infomobility"]["line_id"]

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


