#import xml.etree.ElementTree as ET
from lxml import etree
from datetime import datetime
from math import radians, degrees, sin, cos, atan2, sqrt
import json
import asyncio
import gpsd
import platform


file = "params.json" 


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

# Ripulisci il file params.json
async def clear_params():
    params = open_json(1, file)
    
    params["position_rt"]["latitude"] = 0
    params["position_rt"]["longitude"] = 0
    params["buffer"]["nearby_stops_id"] = []
    params["buffer"]["validazioni_raw"] = []
    params["infomobility"]["line_id"] = ""
    params["infomobility"]["journey"]["last_stop_time"] = ""
    params["infomobility"]["journey"]["stops"] = []
    params["validazioni"] = []
    
    open_json(0, file, params)
    await asyncio.sleep(params["repetition_wait_seconds"]["default"])


############################################################################################
# SEZIONE COORDINATE
############################################################################################


# Funzione per ottenere e stampare i dati GPS
#gpsd.connect() # Connettersi al demone gpsd
def get_gps_data():
    params = open_json(1, file)
    # Ottenere il pacchetto GPS
    packet = gpsd.get_current()
    
    params["position_rt"]["latitude"] = float(packet.lat)
    params["position_rt"]["longitude"] = float(packet.lon)

    print("Dati gps ottenuti: ")
    print(f"Latitudine: {packet.lat}")
    print(f"Longitudine: {packet.lon}")

    open_json(0, file, params)

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
# SEZIONE LXML
############################################################################################


# Inizializza il root 
async def init_lxml():
    global ns, root
    with open(file, "r") as jsonfile:
        params = json.load(jsonfile)
    os = platform.system()
    if os == "Windows":
        netex = params["netex_file"]["path"]["win"] + params["netex_file"]["name"]
    elif os == "Linux":
        netex = params["netex_file"]["path"]["linux"] + params["netex_file"]["name"]
    elif os == "Darwin":
        netex = params["netex_file"]["path"]["mac"] + params["netex_file"]["name"]
    ns = {'ns': params["netex_file"]["namespace"]}
    root = etree.parse(netex) # Carica il file XML
    await asyncio.sleep(params["repetition_wait_seconds"]["default"])

# Ricerca nella struttura filtrando per id
def search_by_id(node, path, id):
    return node.find(f".//ns:{path}[@id='{id}']", namespaces=ns)

# Ricerca nella struttura filtrando per ref
def search_by_ref(node, path, subpath, ref):
    lst = []
    for elem in node.xpath(f".//ns:{path}", namespaces=ns):
        try:
            element = elem.xpath(f".//ns:{subpath}/@ref", namespaces=ns)[0]
        except:
            element = None
        if element == ref:
            lst.append(elem)
    return lst

# trova tutti gli elementi
def search_all(node, path):
    return node.xpath(f".//ns:{path}", namespaces=ns)

# Salva un valore di una foglia
def search_elem(node, path, value):
    try:
        if value == "text":
            element = node.xpath(f".//ns:{path}/text()", namespaces=ns)[0]
        elif value == "ref":
            element = node.xpath(f".//ns:{path}/@ref", namespaces=ns)[0]
        elif value == "last":
            element = node.xpath(f".//ns:{path}[last()]", namespaces=ns)[0]
    except:
        element = None
    return element


############################################################################################
# SEZIONE CALCOLO LINEA
############################################################################################


# Trova il bus corrente e ne memorizza il valore
def calculate_line():
    params = open_json(1, file)
    # Trova tutte le linee che condividono la stessa tratta parziale a partire dalle fermate trovate
    # Una tratta è tra quelle papabili se include tutte le fermate memorizzate fin ora
    lines_id = []
    stops_id = params["infomobility"]["journey"]["stops"]
    for journey in search_all(root, "ServiceJourneyPattern"):
        stops_sjp = []
        for stop in search_all(journey, "ScheduledStopPointRef"):
            stops_sjp.append(stop.get("ref"))
        if set(stops_id) <= set(stops_sjp):
            lines_id.append(search_elem(journey, "LineRef", "ref"))
    return lines_id


async def calculateLine():
    while True:
        params = open_json(1, file)
        #print("LINE: Calcolo linea in corso...")
        lines_id = calculate_line()
        # Se nella lista ci sta una sola linea, allora l'abbiamo trovata
        if len(lines_id) == 1:
            print("LINE: Il codice della linea è: " + lines_id[0])
            params["infomobility"]["line_id"] = lines_id[0]       
            #params["infomobility"]["journeys"] = [] 
        elif len(lines_id) == 0:
            print("LINE: Tratta inesistente. Cancellazione dati temporanei in corso...")
            params["infomobility"]["line_id"] = ""
            params["infomobility"]["stops"] = []
        else:
            print("LINE: Troppe poche fermate conosciute.")
            
        open_json(0, file, params)
        await asyncio.sleep(params["repetition_wait_seconds"]["calculate_line"]) # Attende prima di riattivarsi


############################################################################################
# SEZIONE CALCOLO FERMATA
############################################################################################

# Trova il codice della fermata legata alle info gps
def calculate_stops():
    params = open_json(1, file)
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
            for link in search_by_ref(root, "ServiceLink", "FromPointRef", nearby_stops_id[idx]):
                next_stop_id = search_elem(link, "ToPointRef", "ref")
                stop = search_by_id(root, "ScheduledStopPoint", next_stop_id)
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
    for stop in search_all(root, "ScheduledStopPoint"):
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
        open_json(0, file, params)
            
    return stops


async def calculateStops():
    while True:
        params = open_json(1, file)
        #print("STOPS: Calcolo fermate in corso...")
        #get_gps_data()
        stops = calculate_stops()
        if stops:
            print("STOPS: I codici delle fermate sono: " + str(stops))
            params["infomobility"]["journey"]["last_stop_time"] = str(datetime.now().strftime("%H:%M:%S"))
            for idx in range(len(stops)):
                params["infomobility"]["journey"]["stops"].append(stops[idx])
            open_json(0, file, params)
        else:
            print("STOPS: Nessuna fermata trovata.")
        await asyncio.sleep(params["repetition_wait_seconds"]["calculate_stops"]) # Attende prima di riattivarsi

############################################################################################
# SEZIONE VALIDAZIONE TAP
############################################################################################


# Trova i valori della fermata fisica e tariffaria legati al tap
def calculate_validation(validation):
    params = open_json(1, file)
    # STEP 1
    line_id = params["infomobility"]["line_id"]
    reference_stop_id = validation["__added__"]["last_stop_id"]
    linked_stops = []
    found = False
    # Creazione delle liste di link per ogni tratta
    for journey in search_by_ref(root, "ServiceJourneyPattern", "LineRef", line_id):
        linked_stops. append({
            "id": journey.get("id"),
            "stops": search_all(journey, "ScheduledStopPointRef/@ref")
        })

        # Trovare StopPointInJourneyPattern della fermata di riferimento e del capolinea
        for stop_in_journey in search_by_ref(journey, "StopPointInJourneyPattern", "ScheduledStopPointRef", reference_stop_id):
            reference_journey_id = journey.get("id") # Prendo anche l'id della tratta
            reference_journey_stop_id = stop_in_journey.get("id")
            terminus_journey_stop = search_elem(journey, "StopPointInJourneyPattern", "last")
            terminus_journey_stop_id = terminus_journey_stop.get("id")

    # STEP 2
    time_range = params["time_min_approx"]
    last_stop_time = datetime.strptime(validation["__added__"]["last_stop_time"], "%H:%M:%S")
    difference_times = []
    # Calcola il tempo medio dalla fermata di riferimento al capolinea
    # Considera solo i ServiceJourney della tratta di riferimento di quella fascia oraria
    for service_journey in search_by_ref(root, "ServiceJourney", "ServiceJourneyPatternRef", reference_journey_id):
        for timetable_r in search_by_ref(service_journey, "TimetabledPassingTime", "StopPointInJourneyPatternRef", reference_journey_stop_id):
            stop_sj_time = datetime.strptime(search_elem(timetable_r, "DepartureTime", "text"), "%H:%M:%S")
            difference = (abs(stop_sj_time - last_stop_time).total_seconds() % 3600) // 60 
            if difference < time_range:
                for timetable_t in search_by_ref(service_journey, "TimetabledPassingTime", "StopPointInJourneyPatternRef", terminus_journey_stop_id):
                    terminus_sj_time = datetime.strptime(search_elem(timetable_t, "DepartureTime", "text"), "%H:%M:%S")
                    stop_to_terminus_difference = (terminus_sj_time - stop_sj_time).total_seconds() % 3600 // 60
                    difference_times.append(stop_to_terminus_difference)
    time_stop_to_terminus_avg = sum(difference_times) / len(difference_times) 

    # STEP 3
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
            if item["id"] != reference_journey_id:
                ref_linked = item["stops"]  
    else:
        for item in linked_stops:
            if item["id"] == reference_journey_id:
                ref_linked = item["stops"] 

    # STEP 4
    # Calcolo link e fermata legata al tap
    lat = validation["__added__"]["latitude"]
    lon = validation["__added__"]["longitude"]
    delta = params["position_rt"]["range_meters_approx"]
    link_distance = []
    found = False

    for idx in range(len(ref_linked)):
        stop = search_by_id(root, "ScheduledStopPoint", ref_linked[idx])
        lat_stop = float(search_elem(stop, "Latitude", "text"))
        lon_stop = float(search_elem(stop, "Longitude", "text"))
        distance = calculate_distance(lat, lon, lat_stop, lon_stop)
        if distance <= delta:
            tariff_zone_id = search_elem(stop, "TariffZoneRef", "ref")
            tariff_zone = search_by_id(root, "TariffZone", tariff_zone_id)
            fermata_tariffaria = int(search_elem(tariff_zone, "Name", "text") or 000)
            fermata_fisica = int(search_elem(stop, "PublicCode", "text") or 0000)
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
        stop = search_by_id(root, "ScheduledStopPoint", ref_linked[idx])
        tariff_zone_id = search_elem(stop, "TariffZoneRef", "ref")
        tariff_zone = search_by_id(root, "TariffZone", tariff_zone_id)
        fermata_tariffaria = int(search_elem(tariff_zone, "Name", "text") or 000)
        fermata_fisica = int(search_elem(stop, "PublicCode", "text") or 0000)
    line = search_by_id(root, "Line", line_id)
    linea = search_elem(line, "Name", "text")
    return fermata_fisica, fermata_tariffaria, linea
    

async def calculateValidations():
    while True:
        #print("VALIDATIONS: Calcolo validazioni in corso...")
        params = open_json(1, file)
        validazioni = params["validazioni"]
        line_id = params["infomobility"]["line_id"]

        if line_id == "":
            pass
            #print("VALIDATIONS: Operazione annullata. Linea ancora non trovata.")
        elif not validazioni:
            pass
            #print("VALIDATIONS: Operazione annullata. Nessuna validazione da calcolare.")

        if params["infomobility"]["line_id"] != "" and validazioni:
            fermata_fisica, fermata_tariffaria, linea = calculate_validation(validazioni[0])
            params["validazioni"][0]["fermata"] = fermata_fisica
            params["validazioni"][0]["codice_fermata_tariffaria"] = fermata_tariffaria
            params["validazioni"][0]["codice_linea"] = linea
            params["validazioni"][0].pop("__added__")
            print("VALIDATIONS: Validazione in output!")
            print(params["validazioni"][0])
            params["validazioni"].pop(0)
            open_json(0, file, params)
        await asyncio.sleep(params["repetition_wait_seconds"]["default"])  # Attende prima di riattivarsi

async def define_tap():
    while True:
        params = open_json(1, file)
        validazioni_raw = params["buffer"]["validazioni_raw"]
        if validazioni_raw and params["infomobility"]["journey"]["stops"]:
            if validazioni_raw[0] not in ["check-in", "check-out", 0, 1]:
                print("TAP: Tap non riconosciuto.")
            else:
                if validazioni_raw[0] in ["check-in", 0]:
                    operazione = "check-in"
                else:
                    operazione = "check-out"
                #get_gps_data()
                params["validazioni"].append(
                    {
                        "data_validazione": str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                        "vettore_validazione": "ANM",
                        "veicolo": "",
                        "dispositivo": "",
                        "pnr_seriale": 0,
                        "supporto": "",
                        "operazione": operazione,
                        "esito": "",
                        "emv_terminal_id": 0,
                        "emv_hashpan": "",
                        "fermata": 0,
                        "codice_fermata_tariffaria": 0,
                        "codice_linea": "",
                        "__added__": {
                            "latitude": params["position_rt"]["latitude"],
                            "longitude": params["position_rt"]["longitude"],
                            "last_stop_id": params["infomobility"]["journey"]["stops"][-1],
                            "last_stop_time": params["infomobility"]["journey"]["last_stop_time"]
                        }
                    }
                )
                print("TAP: Tap registato correttamente.")

            params["buffer"]["validazioni_raw"].pop(0)
            open_json(0, file, params)
        await asyncio.sleep(params["repetition_wait_seconds"]["default"]) # Attende prima di riattivarsi


############################################################################################
# SEZIONE THREADING & MAIN
############################################################################################


async def main():
    print("Inizializzazione Tap&Go on Bus in corso...")
    init_params_task = asyncio.create_task(clear_params())
    await init_params_task # Attende che il task sia completato
    init_lxml_task = asyncio.create_task(init_lxml())
    await init_lxml_task # Attende che il task sia completato
    print("Inizializzazione Tap&Go on Bus competata!")

    # Crea i task per le funzioni
    line_task = asyncio.create_task(calculateLine())
    stops_task = asyncio.create_task(calculateStops())
    validations_task = asyncio.create_task(calculateValidations())
    tap_task = asyncio.create_task(define_tap())
    await asyncio.gather(line_task, stops_task, validations_task, tap_task) # Attende che tutti i task sia completati


# Esegue il loop principale
asyncio.run(main())
