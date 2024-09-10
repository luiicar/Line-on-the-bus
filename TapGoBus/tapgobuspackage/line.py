import asyncio
import logging

from .config import file_params
from .file_opener import open_json
from .parser import search_all, search_elem, get_root

# Creazione di un logger specifico per questo modulo con nome personalizzato
logger = logging.getLogger("[ LINE ]")


# Trova il bus corrente e ne memorizza il valore
def calculate_line():
    params = open_json(1, file_params)
    # Trova tutte le linee che condividono la stessa tratta parziale a partire dalle fermate trovate
    # Una tratta è tra quelle papabili se include tutte le fermate nello stesso ordine in cui sono memorizzate fin ora
    lines_id = []
    stops_id = params["infomobility"]["journey"]["stops"]
    for journey in search_all(get_root(), "ServiceJourneyPattern"):
        stops_sjp, idx = [], 0
        if stops_id:
            for stop in search_all(journey, "ScheduledStopPointRef"):
                stops_sjp.append(stop.get("ref"))
            for stop in stops_sjp:
                if stop == stops_id[idx]:
                    idx += 1
                    if idx == len(stops_id):
                        lines_id.append(search_elem(journey, "LineRef", "ref"))
                        break
    return lines_id


async def calculateLine():
    while True:
        params = open_json(1, file_params)
        found, delete = False, False

        if params["infomobility"]["journey"]["stops"]:
            lines_id = calculate_line()
            # Se nella lista ci sta una sola linea, allora l'abbiamo trovata
            if len(lines_id) == 1:
                found = True  
            elif len(lines_id) == 0:
                if params["infomobility"]["line_id"] != "":
                    # Verifica se l'ultima fermata trovata è attraversata dall'autobus precedentemente trovato in cerca di continuità
                    params["infomobility"]["journey"]["stops"] = params["infomobility"]["journey"]["stops"][-1:]
                    open_json(0, file_params, params)
                    lines_id = calculate_line()
                    if params["infomobility"]["line_id"] not in lines_id:
                        delete = True
                    else:
                        lines_id.insert(0, params["infomobility"]["line_id"])
                        found = True
                else: 
                    delete = True
            elif len(lines_id) > 1:
                if params["infomobility"]["line_id"] != "":
                    # Verifica se tra gli autobus c'è quello precedentemente trovato in cerca di continuità
                    if params["infomobility"]["line_id"] in lines_id:
                        found = True

        if found:
            logger.info("Il codice della linea: %s", lines_id[0])
            params["infomobility"]["line_id"] = lines_id[0] 
        else:
            logger.info("Troppe poche fermate conosciute.")
        if delete:
            logger.info("Tratta inesistente. Cancellazione dati temporanei sulle fermate in corso...")
            params["infomobility"]["line_id"] = ""
            params["infomobility"]["journey"]["stops"] = []
        open_json(0, file_params, params)
        await asyncio.sleep(params["repetition_wait_seconds"]["calculate_line"]) # Attende prima di riattivarsi




