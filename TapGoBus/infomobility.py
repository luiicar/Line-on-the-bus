#import xml.etree.ElementTree as ET
from lxml import etree
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
# SEZIONE INFOMOBILITà
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
                    "Code": stop.xpath("ns:PublicCode/text()", namespaces=ns)[0],
                    "latitude": float(stop.xpath(".//ns:Latitude/text()", namespaces=ns)[0]),
                    "longitude": float(stop.xpath(".//ns:Longitude/text()", namespaces=ns)[0])
                }
                stops.append(stopinfo)
            for sj in root.xpath(f".//ns:ServiceJourney", namespaces=ns):
                if sj.xpath(f"ns:ServiceJourneyPatternRef/@ref", namespaces=ns)[0] == sjp.get("id"):
                    temporal_info[sj.xpath("ns:DepartureTime/text()", namespaces=ns)[0]] = sj.xpath("ns:JourneyDuration/text()", namespaces=ns)[0]
            journeyinfo = {
                "id": sjp.get("id"),
                #"direction": sjp.xpath("ns:DirectionType/text()", namespaces=ns)[0],
                "departure/duration": dict(sorted(temporal_info.items())),
                "stops": stops
            }
            file["journeys"].append(journeyinfo)
    open_json(0, filename, file)


############################################################################################
# SEZIONE MAIN
############################################################################################


def main():
    getInfomobility()

if __name__ == "__main__":
    main()