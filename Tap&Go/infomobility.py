import xml.etree.ElementTree as ET
import math
import json

############################################################################################
# SEZIONE FILEs
############################################################################################

# Apre il lettura o scittura i file JSON
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


# Crea una lista di codici fermata appartenenti ad una stessa direzione 
def create_list_ids(lst, direction):
    list_ids = []
    for item in lst:
        if item["direction"] == direction:
            sublist = item["stops"]
            list_ids.extend(sub["id"] for sub in sublist)
    return list_ids


# Trova tutte le linee che condividono la stessa tratta parziale
def find_lines(stops, root, ns):
    lines = []
    for sjp in root.findall(f".//{ns}ServiceJourneyPattern"):
        stops_ref = {r.get("ref") for r in sjp.findall(f".//{ns}ScheduledStopPointRef")}
        if set(stops) <= set(stops_ref):
            lines_ref = sjp.find(f".//{ns}LineRef")
            lines.append(lines_ref.get("ref"))
    return lines


# Trova il bus corrente e ne memorizza il valore
def calculateLine(file):
    params = open_json(1, file)
    netex = params["netex"]["netex_file_path"] + params["netex"]["netex_file_name"]
    ns = params["netex"]["namespace"]

    journey_patterns = params["infomobility"]["JourneyPattern"]
    
    # Carica il file XML
    root = ET.parse(netex)

    linee_in, linee_out, linee_un = [], [], []

    stops_inbound_id = create_list_ids(journey_patterns, "inbound")
    if stops_inbound_id:
        linee_in= find_lines(list(set(stops_inbound_id)), root, ns)
    stops_outbound_id = create_list_ids(journey_patterns, "outbound")
    if stops_outbound_id:
        linee_out= find_lines(list(set(stops_outbound_id)), root, ns)
    stops_unbound_id = create_list_ids(journey_patterns, "")
    if stops_unbound_id:
        linee_un= find_lines(list(set(stops_unbound_id)), root, ns)

    linee = linee_in + linee_out + linee_un
    unique_lines = list(set(linee))
    if len(unique_lines) == 1:
        linea = root.find(f".//{ns}Line[@id='" + unique_lines[0] + "']")

        params["infomobility"]["Line"]["id"] = linea.get("id")
        params["infomobility"]["Line"]["name"] = linea.findtext(f"{ns}Name")
        journey_patterns = []
        open_json(0, file, params)

    elif len(unique_lines) == 0:
        journey_patterns = []
        open_json(0, file, params)


############################################################################################
# SEZIONE CALCOLO FERMATA
############################################################################################


# Funzione per calcolare la distanza tra due punti geografici
def calculate_distance(lat1, lon1, lat2, lon2):
    raggio_terra = 6371000  # Raggio medio della Terra in metri
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = math.sin(delta_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distanza = raggio_terra * c
    return distanza


def search_dict(lst, value):
    for dict in lst:
        if dict["direction"] == value:
            return dict


# Funzione per scoprire la fermata al quale il bus si ferma 
def calculateStop_due_to_search(file):
    params = open_json(1, file)

    netex = params["netex"]["netex_file_path"] + params["netex"]["netex_file_name"]
    ns = params["netex"]["namespace"]

    journey_patterns = params["infomobility"]["JourneyPattern"]
    unbound = search_dict(journey_patterns, "")
    if not unbound:
        journey_patterns.append(
            {
                "id": "",
                "direction": "",
                "stops": []
            }
        )


    lat = params["position_rt"]["latitude"]
    lon = params["position_rt"]["longitude"]
    delta = params["position_rt"]["range_meters_approx"]

    # Carica il file XML
    root = ET.parse(netex)

    # Trova tutte le fermate degli autobus
    fermate = root.findall(f".//{ns}ScheduledStopPoint")

    # Trova le fermate più vicine
    fermate_vicine = []
    for fermata in fermate:
        lat_stop = float(fermata.findtext(f".//{ns}Latitude"))
        lon_stop = float(fermata.findtext(f".//{ns}Longitude"))
        distanza = calculate_distance(lat, lon, lat_stop, lon_stop)
        if distanza <= delta:
            fermate_vicine.append({"id": fermata.get("id"), "name": fermata.findtext(f"{ns}ShortName")})

    # Se trova 1 fermata la si memorizza (sperando sia giusta)
    if len(fermate_vicine) == 1:
        for idx in range(len(journey_patterns)):
            if journey_patterns[idx]["direction"] == "":
                journey_patterns[idx]["stops"].append(fermate_vicine[0])

    # Se trova più fermate si cerca di capire il verso del bus
    # le prossime coordinate gps ce lo diranno
    # se il "link to" si allontana mentre ad uno si avvicina, si più filtrare
    #elif len(fermate_vicine) > 1:
        #for idx in range(len(fermate_vicine)):     
        #    break  

    # Se non si trovano fermate  si cerca la fermata più vicina a noi
    # da lì cercare di capire se è la nostra meta oppure veniamo da lì
    #else:
        #fermate = root.findall(f".//{ns}ScheduledStopPoint")
        #for fermata in fermate:
            #stop_id = fermata.get("id")
            #stop_name = fermata.findtext(f"{ns}Name")
            #lat_stop = float(fermata.findtext(f".//{ns}Latitude"))
            #lon_stop = float(fermata.findtext(f".//{ns}Longitude"))
            #distanza = calculate_distance(lat, lon, lat_stop, lon_stop)
            #if distanza < min_distance:
                #min_distance = distanza
                #closest_stop = {"id": stop_id, "name": stop_name}
    
    open_json(0, file, params)
    # Se comunque resta il dubbio, non si memorizza nessuna fermata


# Funzione per scoprire la fermata al quale il bus si ferma 
def calculateStop_due_to_validation(file):
    params = open_json(1, file)

    netex = params["netex"]["netex_file_path"] + params["netex"]["netex_file_name"]
    ns = params["netex"]["namespace"]

    journey_patterns = params["infomobility"]["JourneyPattern"]


############################################################################################
# SEZIONE INFOMOBILITà ADMIN
############################################################################################


def getInfomobility(file):
    params = open_json(1, file)
    netex = params["netex"]["netex_file_path"] + params["netex"]["netex_file_name"]
    ns = params["netex"]["namespace"]

    journey_patterns = params["infomobility"]["JourneyPattern"]
    line_id = params["infomobility"]["Line"]["id"]
    
    # Carica il file XML
    root = ET.parse(netex)

    #Se è in memoria la linea, elimina le tratte trovate fin ora e aggiungi tutte
    if line_id:
        journey_patterns = []

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

                journey_patterns.append({
                    "id": journey_id,
                    "direction": direction,
                    "stops": stops
                })

    open_json(0, file, params)


