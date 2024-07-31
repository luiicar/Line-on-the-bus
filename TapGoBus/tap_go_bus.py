#import xml.etree.ElementTree as ET
from lxml import etree
from datetime import datetime
from math import radians, degrees, sin, cos, atan2, sqrt
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
# SEZIONE COORDINATE
############################################################################################


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
        ref_stop_id = params["validazioni"][0]["__added__"]["last_stop_id"]
        
        linked_stops_id = []
        for sjp in root.xpath(".//ns:ServiceJourneyPattern", namespaces=ns):
            # Creazione delle liste di link per ogni tratta
            if sjp.xpath(".//ns:LineRef/@ref", namespaces=ns)[0] == line_id:
                linked_stops_id. append({
                    "id": sjp.get("id"),
                    "stops": sjp.xpath(".//ns:ScheduledStopPointRef/@ref", namespaces=ns)
                })
                # Conversione codice ScheduledStopPoint a codice StopPointInJourneyPattern della fermata di riferimento
                for spinjp in sjp.xpath(".//ns:StopPointInJourneyPattern", namespaces=ns):
                    if spinjp.xpath(".//ns:ScheduledStopPointRef/@ref", namespaces=ns)[0] == ref_stop_id:
                        ref_journey_id = sjp.get("id")
                        
                        journey_stop_id_raw = spinjp.get("id")
                        trim1 = journey_stop_id_raw.rfind(":")
                        trim2 = journey_stop_id_raw.find("_")
                        value1 = journey_stop_id_raw[:trim1 + 1]
                        value2 = journey_stop_id_raw[trim2 + 1:]
                        journey_stop_id = value1 + value2
        
        # Step 2
        time_range = params["time_min_approx"]
        valid_stop_time = datetime.strptime(params["validazioni"][0]["__added__"]["last_stop_time"], "%H:%M:%S")
        difference_times = []
        # Calcola il tempo medio dalla fermata di riferimento al capolinea
        # Considera solo i ServiceJourney della tratta di riferimento di quella fascia oraria
        while not difference_times:
            for sj in root.xpath(".//ns:ServiceJourney", namespaces=ns):
                if sj.xpath(".//ns:ServiceJourneyPatternRef/@ref", namespaces=ns)[0] == ref_journey_id:
                    for tpt in sj.xpath(".//ns:TimetabledPassingTime", namespaces=ns):
                        if tpt.xpath("ns:StopPointInJourneyPatternRef/@ref", namespaces=ns)[0] == journey_stop_id:
                            stop_sj_time_str = tpt.xpath("ns:DepartureTime/text()", namespaces=ns)[0]
                            stop_sj_time = datetime.strptime(stop_sj_time_str, "%H:%M:%S")
                            difference = abs(stop_sj_time - valid_stop_time)
                            difference_min = (difference.seconds % 3600) // 60
                            if difference_min < time_range:
                                terminus_time_sj_str = sj.findtext(".//ns:DepartureTime[last()]", namespaces=ns)
                                terminus_sj_time = datetime.strptime(terminus_time_sj_str, "%H:%M:%S")
                                time_stop_to_terminus = terminus_sj_time - stop_sj_time
                                time_stop_to_terminus_min = (time_stop_to_terminus.seconds % 3600) // 60
                                difference_times.append(time_stop_to_terminus_min)
            if difference_times:
                time_stop_to_terminus_avg = sum(difference_times) / len(difference_times) 
            else:
                trim = journey_stop_id.find(params["vector"])
                value1 = journey_stop_id[:trim - 2]
                value2 = journey_stop_id[trim:]
                journey_stop_id = value1 + value2


        # Step 3
        # Capire qual'è la tratta di riferimento per il calcolo della validazione
        # Se l'orario della validazione è minore del tempo medio per arrivare al capolinea, la tratta è quella, altrimenti è l'altra
        valid_date_str = params["validazioni"][0]["data_validazione"]
        start_trim = valid_date_str.rfind(" ")
        valid_time_str = valid_date_str[start_trim + 1:]
        valid_date_time = datetime.strptime(valid_time_str, "%H:%M:%S")
        
        if stop_sj_time + time_stop_to_terminus_avg > valid_date_time:
            for item in linked_stops_id:
                if item["id"] != ref_journey_id:
                    ref_linked = item["stops"]  
        else:
            for item in linked_stops_id:
                if item["id"] == ref_journey_id:
                    ref_linked = item["stops"]  

        # Step 4
        # Calcolo link e fermata legata al tap
        lat = validazioni[0]["__added__"]["latitude"]
        lon = validazioni[0]["__added__"]["longitude"]
        delta = params["position_rt"]["range_meters_approx"]

        link_distance = []
        found = False

        for idx in range(len(ref_linked)):
            stop = root.find(f".//ns:ScheduledStopPoint[@id='{ref_linked[idx]}']", namespaces=ns)[0]
            lat_stop = float(stop.xpath(".//ns:Latitude/text()", namespaces=ns)[0])
            lon_stop = float(stop.xpath(".//ns:Longitude/text()", namespaces=ns)[0])
            distance = calculate_distance(lat, lon, lat_stop, lon_stop)
            if distance <= delta:
                tariff_zone_id = stop.xpath(".//ns:TariffZoneRef/@ref", namespaces=ns)[0]
                params["validazioni"][0]["fermata"] = estract_stop_id(ref_linked[idx])
                params["validazioni"][0]["codice fermata_tariffaria"] = estract_tariffzone_id(tariff_zone_id)
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
            if validazioni[0]["operazione"] == "check-in":
                idx = link_distance.index(min(link_distance))
            elif validazioni[0]["operazione"] == "check-out":
                idx = link_distance.index(min(link_distance)) + 1
            stop = root.find(f".//ns:ScheduledStopPoint[@id='{ref_linked[idx]}']", namespaces=ns)[0]
            tariff_zone_id = stop.xpath(".//ns:TariffZoneRef/@ref", namespaces=ns)[0]
            params["validazioni"][0]["fermata"] = estract_stop_id(ref_linked[idx])
            params["validazioni"][0]["codice fermata_tariffaria"] = estract_tariffzone_id(tariff_zone_id)

        params["validazioni"][0]["codice_linea"] = estract_line_id(line_id)
        #params["validazioni"][0] = []
        open_json(0, file, params)


############################################################################################
# SEZIONE INFOMOBILITà ----- PER TEST SIMULATI
############################################################################################


# Crea un file json che, dato in input il nome di un bus, ci da tutte le informaziono utili
def getInfomobility():
    file, file["line"] = {}, {}
    file["line"]["id"] = "None"
    file["journeys"] = []

    exist = False
    while not exist:
        name = input("Inserire il nome del bus: ").upper()
        filename = "infomobility-" + name + ".json"

        for l in root.xpath(".//ns:Line", namespaces=ns):
            if l.xpath("ns:Name/text()", namespaces=ns)[0] == name:
                file["line"]["id"] = l.get("id")
                file["line"]["name"] = l.xpath("ns:Name/text()", namespaces=ns)[0]
                break
        if file["line"]["id"] == "None":
            print("Autobus non trovato")
        else:
            exist = True

    for sjp in root.xpath(".//ns:ServiceJourneyPattern", namespaces=ns):
        if sjp.xpath(".//ns:LineRef/@ref", namespaces=ns)[0] == file["line"]["id"]:
            stops = []
            temporal_info = {}
            for sspref in sjp.xpath(".//ns:ScheduledStopPointRef/@ref", namespaces=ns):
                stop = root.find(f".//ns:ScheduledStopPoint[@id='{sspref}']", namespaces=ns)
                stopinfo = {
                    "id": sspref,
                    "Name": stop.xpath("ns:ShortName/text()", namespaces=ns)[0],
                    "Longitude": float(stop.xpath(".//ns:Longitude/text()", namespaces=ns)[0]),
                    "Latitude": float(stop.xpath(".//ns:Latitude/text()", namespaces=ns)[0])
                }
                stops.append(stopinfo)
            for sj in root.xpath(f".//ns:ServiceJourney", namespaces=ns):
                if sj.xpath(f"ns:ServiceJourneyPatternRef/@ref", namespaces=ns)[0] == sjp.get("id"):
                    temporal_info[sj.xpath("ns:DepartureTime/text()", namespaces=ns)[0]] = sj.xpath("ns:JourneyDuration/text()", namespaces=ns)[0]
            journeyinfo = {
                "id": sjp.get("id"),
                "direction": sjp.xpath("ns:DirectionType/text()", namespaces=ns)[0],
                "departure/duration": dict(sorted(temporal_info.items())),
                "stops": stops
            }
            file["journeys"].append(journeyinfo)
    open_json(0, filename, file)

            


