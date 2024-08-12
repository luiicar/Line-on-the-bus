#import xml.etree.ElementTree as ET
from lxml import etree
from datetime import datetime
from math import radians, degrees, sin, cos, atan2, sqrt
import json
import asyncio
import gpsd


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

async def clear_params():
    params = {
        "vector": "ANM",
        "netex": {
            "netex_file_name": "IT-IT-ITF3-ANM_GOMMANeTEx_L2.xml",
            "netex_file_path": "C:/Users/Jalexus/Desktop/Tap-Go/TapGoBus/",
            "namespace": "http://www.netex.org.uk/netex"
        },
        "position_rt": {
            "latitude": 0,
            "longitude": 0,
            "range_meters_approx": 5
        },
        "time_min_approx": 45,
        "buffer": {
            "nearby_stops_id": []
        },
        "infomobility": {
            "line_id": "",
            "journey": {
                "last_stop_time": "",
                "stops": []
            }
        },
        "validazioni": []
    }
    open_json(1, file, params)
    await asyncio.sleep(1)


############################################################################################
# SEZIONE COORDINATE
############################################################################################


# Funzione per ottenere e stampare i dati GPS
#gpsd.connect() # Connettersi al demone gpsd
def get_gps_data():
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

# Ricerca nella struttura filtrando per id
def search_by_id(node, path, id):
    return node.find(f".//ns:{path}[@id='{id}']", namespaces=ns)

# Ricerca nella struttura filtrando per ref
def search_by_ref(node, path, subpath, ref):
    lst = []
    for elem in node.xpath(f".//ns:{path}", namespaces=ns):
        if elem.xpath(f".//ns:{subpath}/@ref", namespaces=ns)[0] == ref:
            lst.append(elem)
    return lst

# trova tutti gli elementi
def search_all(node, path):
    return node.xpath(f".//ns:{path}", namespaces=ns)

# Salva un valore di una foglia
def search_elem(node, path, value):
    if value == "text":
        return node.xpath(f".//ns:{path}/text()", namespaces=ns)[0]
    elif value == "ref":
        return node.xpath(f".//ns:{path}/@ref", namespaces=ns)[0]
    elif value == "last":
        return node.xpath(f".//ns:{path}[last()]", namespaces=ns)[0]


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
        print("LINE: Calcolo linea in corso...")
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
        await asyncio.sleep(300) # Attende 5 min prima di riattivarsi


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

    # Se trova una fermata la si memorizza (sperando sia giusta)
    if len(nearby) == 1:
        stops.append(nearby_stops_id[index])

    # Se trovano più fermate si cerca di capire il verso del bus
    # le prossime coordinate gps ce lo diranno quindi per il momento salviamo in buffer le fermate
    elif len(nearby) > 1:
        params["buffer"]["nearby_stops_id"] = nearby
        open_json(0, file, params)
            
    return stops


async def calculateStops():
    while True:
        print("STOPS: Calcolo fermate in corso...")
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
        await asyncio.sleep(60) # Attende 1 min prima di riattivarsi

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


# Converti codice StopPointInJourneyPattern nella forma corretta
def trim_journey_stop_id(testo):
    trim1 = testo.rfind(":")
    trim2 = testo.find("_")
    value1 = testo[:trim1 + 1]
    value2 = testo[trim2 + 1:]
    return value1 + value2


# Ulteriore taglio di StopPointInJourneyPattern per problemi di compatibilità
def more_trim_journey_stop_id(testo, vettore):
    trim = testo.find(vettore)
    value1 = testo[:trim - 2]
    value2 = testo[trim:]
    return value1 + value2


# Trova i valori della fermata fisica e tariffaria legati al tap
def calculate_validation(validation):
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
            reference_journey_stop_id = trim_journey_stop_id(stop_in_journey.get("id"))
            terminus_journey_stop = search_elem(journey, "StopPointInJourneyPattern", "last")
            terminus_journey_stop_id = trim_journey_stop_id(terminus_journey_stop.get("id"))

    # STEP 2
    time_range = params["time_min_approx"]
    last_stop_time = datetime.strptime(validation["__added__"]["last_stop_time"], "%H:%M:%S")
    difference_times = []
    # Calcola il tempo medio dalla fermata di riferimento al capolinea
    # Considera solo i ServiceJourney della tratta di riferimento di quella fascia oraria
    while not difference_times:
        for service_journey in search_by_ref(root, "ServiceJourney", "ServiceJourneyPatternRef", reference_journey_id):
            for timetable_r in search_by_ref(service_journey, "TimetabledPassingTime", "StopPointInJourneyPatternRef", reference_journey_stop_id):
                stop_sj_time = datetime.strptime(search_elem(timetable_r, "DepartureTime", "text"), "%H:%M:%S")
                difference = (abs(stop_sj_time - last_stop_time).total_seconds() % 3600) // 60 
                if difference < time_range:
                    for timetable_t in search_by_ref(service_journey, "TimetabledPassingTime", "StopPointInJourneyPatternRef", terminus_journey_stop_id):
                        terminus_sj_time = datetime.strptime(search_elem(timetable_t, "DepartureTime", "text"), "%H:%M:%S")
                        stop_to_terminus_difference = (terminus_sj_time - stop_sj_time).total_seconds() % 3600 // 60
                        difference_times.append(stop_to_terminus_difference)
        if difference_times:
            time_stop_to_terminus_avg = sum(difference_times) / len(difference_times) 
        else:
            reference_journey_stop_id = more_trim_journey_stop_id(reference_journey_stop_id, params["vector"])
            terminus_journey_stop_id = more_trim_journey_stop_id(terminus_journey_stop_id, params["vector"])

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
            fermata_fisica = estract_stop_id(ref_linked[idx])
            fermata_tariffaria = estract_tariffzone_id(tariff_zone_id)
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
        fermata_fisica = estract_stop_id(ref_linked[idx])
        fermata_tariffaria = estract_tariffzone_id(tariff_zone_id)
    return fermata_fisica, fermata_tariffaria
    

async def calculateValidations():
    while True:
        print("VALIDATIONS: Calcolo validazioni in corso...")
        params = open_json(1, file)
        validazioni = params["validazioni"]
        line_id = params["infomobility"]["line_id"]

        if line_id == "":
            print("VALIDATIONS: Operazione annullata. Linea ancora non trovata.")
        elif not validazioni:
            print("VALIDATIONS: Operazione annullata. Nessuna validazione da calcolare.")

        if params["infomobility"]["line_id"] != "" and validazioni: #while
            fermata_fisica, fermata_tariffaria = calculate_validation(validazioni[0])
            params["validazioni"][0]["fermata"] = fermata_fisica
            params["validazioni"][0]["codice_fermata_tariffaria"] = fermata_tariffaria
            params["validazioni"][0]["codice_linea"] = estract_line_id(line_id)
            #params["validazioni"][0].pop("__added__")
            print("VALIDATIONS: Validazione in output!")
            #params["validazioni"].pop(0)
            open_json(0, file, params)
            params["validazioni"][0].pop("__added__")
            print(params["validazioni"][0])
        await asyncio.sleep(1)  # Attende 1 sec prima di riattivarsi


############################################################################################
# SEZIONE THREADING & MAIN
############################################################################################


async def main():
    #print("Inizializzazione Tap&Go on Bus in corso...")
    init_task = asyncio.create_task(clear_params())
    await init_task # Attende che il task sia completato
    print("Inizializzazione Tap&Go on Bus competata!")

    # Crea i task per le funzioni
    line_task = asyncio.create_task(calculateLine())
    stops_task = asyncio.create_task(calculateStops())
    validations_task = asyncio.create_task(calculateValidations())
    await asyncio.gather(line_task, stops_task, validations_task) # Attende che tutti i task sia completati

# Esegue il loop principale
asyncio.run(main())
