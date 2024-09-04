from datetime import datetime
import asyncio
import logging

from .config import file_params
from .file_opener import open_json
from .coordinates import get_gps_data

# Creazione di un logger specifico per questo modulo con nome personalizzato
logger = logging.getLogger("[ TAP ]")


async def define_tap():
    while True:
        params = open_json(1, file_params)
        validazioni_raw = params["buffer"]["validazioni_raw"]
        if validazioni_raw and params["infomobility"]["journey"]["stops"]:
            if validazioni_raw[0] not in ["check-in", "check-out", 0, 1]:
                logger.info("[ TAP ] Tap non riconosciuto.")
            else:
                if validazioni_raw[0] in ["check-in", 0]:
                    operazione = "check-in"
                else:
                    operazione = "check-out"
                get_gps_data()
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
                logger.info("[ TAP ] Tap memorizzato correttamente.")

            params["buffer"]["validazioni_raw"].pop(0)
            open_json(0, file_params, params)
        await asyncio.sleep(params["repetition_wait_seconds"]["default"]) 
