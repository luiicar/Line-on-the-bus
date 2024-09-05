import asyncio

from tapgobuspackage.file_opener import open_json
from tapgobuspackage.parser import init_lxml, get_root, search_all, search_elem, search_by_id


# Crea un file json che, dato in input il nome di un bus, ci da tutte le informaziono utili
async def main():
    await init_lxml()
    file, file["line"] = {}, {}
    file["line"]["id"] = "None"
    file["journeys"] = []

    exist = False
    linee = []

    lines = search_all(get_root(), "Line")
    for line in lines:
        linee.append(search_elem(line, "Name", "text"))
    print("Lista degli autobus:")
    print(linee)

    while not exist:
        name = input(">>> Inserire il nome del bus: ").upper()
        filename = "database/infomobility-" + name + ".json"

        for line in lines:
            if search_elem(line, "Name", "text") == name:
                file["line"]["id"] = line.get("id")
                file["line"]["name"] = name
                break
        if file["line"]["id"] == "None":
            print("Autobus non trovato")
        else:
            exist = True

    departure = input(">>> Stampare elenco departure/duration? [y/N] ").upper()

    patterns = search_all(get_root(), "ServiceJourneyPattern")
    for pattern in patterns:
        if search_elem(pattern, "LineRef", "ref") == file["line"]["id"]:
            stops = []
            temporal_info = {}
            stops_pattern = search_all(pattern, "ScheduledStopPointRef/@ref")
            for stop_pattern in stops_pattern:
                stop = search_by_id(get_root(), "ScheduledStopPoint", stop_pattern)
                stopinfo = {
                    "id": stop.get("id"),
                    "Name": search_elem(stop, "ShortName", "text"),
                    "Code": search_elem(stop, "PublicCode", "text"),
                    "latitude": float(search_elem(stop, "Latitude", "text")),
                    "longitude": float(search_elem(stop, "Longitude", "text"))
                }
                stops.append(stopinfo)
            
            departure_duration = {}

            if departure == "Y":
                service_journeys = search_all(get_root(), "ServiceJourney")
                for service_journey in service_journeys:
                    if search_elem(service_journey, "ServiceJourneyPatternRef", "ref") == pattern.get("id"):
                        temporal_info[search_elem(service_journey, "DepartureTime", "text")] = search_elem(service_journey, "JourneyDuration", "text")
                departure_duration = dict(sorted(temporal_info.items()))
            journeyinfo = {
                "id": stop_pattern,
                #"direction": sjp.xpath("ns:DirectionType/text()", namespaces=ns)[0],
                "departure/duration": departure_duration,
                "stops": stops
            }
            file["journeys"].append(journeyinfo)
    open_json(0, filename, file)



# Esegue il loop principale
asyncio.run(main())