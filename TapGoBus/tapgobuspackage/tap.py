from datetime import datetime
import asyncio
import logging

from .config import file_params
from .file_opener import open_json
from .coordinates import get_gps_data
from .simulation import sim_gps_tap

# Creazione di un logger specifico per questo modulo con nome personalizzato
logger = logging.getLogger("[ TAP ]")


async def define_tap(flag, sim_file):
    while True:
        params = open_json(1, file_params)
        validazioni_raw = params["buffer"]["validazioni_raw"]
        if validazioni_raw and params["infomobility"]["journey"]["stops"]:
            if validazioni_raw[0] not in ["check-in", "check-out", 0, 1]:
                logger.info("Tap non riconosciuto.")
            else:
                if validazioni_raw[0] in ["check-in", 0]:
                    operazione = "check-in"
                else:
                    operazione = "check-out"
                
                if flag:
                    lat, lon = sim_gps_tap(params["infomobility"]["journey"]["stops"][-1], sim_file)
                else:
                    get_gps_data()
                    lat = params["position_rt"]["latitude"]
                    lon = params["position_rt"]["longitude"]

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
                            "latitude": lat,
                            "longitude": lon,
                            "last_stop_id": params["infomobility"]["journey"]["stops"][-1],
                            "last_stop_time": params["infomobility"]["journey"]["last_stop_time"]
                        }
                    }
                )
                logger.info("Tap memorizzato correttamente.")

            params["buffer"]["validazioni_raw"].pop(0)
            open_json(0, file_params, params)
        await asyncio.sleep(params["repetition_wait_seconds"]["default"]) 
