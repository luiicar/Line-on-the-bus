import logging
import asyncio

from BusFleetPy.config import file_log
from BusFleetPy.file_opener import open_json
from BusFleetPy.parser import init_lxml, init_pd, init_database
from BusFleetPy.coordinates import get_gpsd_connection
from BusFleetPy.tap import define_tap
from BusFleetPy.line import calculateLine
from BusFleetPy.stop import calculateStops
from BusFleetPy.validation import calculateValidations
from BusFleetPy.simulation import simulate, get_sim

# Configurazione del logging
logging.basicConfig(filename=file_log, level=logging.DEBUG, format='%(asctime)s - %(name)s %(message)s')

# Creazione di un logger specifico per questo modulo con nome personalizzato
logger = logging.getLogger(" ")


async def main():
    sim = False

    open_json(0, file_log, option="clear")
    logger.info("Inizializzazione Tap&Go on Bus in corso...")
    await init_lxml()
    await init_pd()
    await init_database()
    connected = await get_gpsd_connection()
    sim_file = await get_sim()
    if connected:
        logger.info("Connessione al GPS Deamon riuscita.")
    elif not connected and sim_file == "":
        logger.info("Connessione al GPS Deamon fallita. Le coordinate dovrenno essere inserite manualmente.")
    else:
        logger.info("Connessione al GPS Deamon fallita. Le coordinate verranno simulate.")
        sim = True
    logger.info("Inizializzazione Tap&Go on Bus completata!")

    # Crea i task per le funzioni
    line_task = asyncio.create_task(calculateLine())
    stops_task = asyncio.create_task(calculateStops())
    validations_task = asyncio.create_task(calculateValidations())
    tap_task = asyncio.create_task(define_tap(sim))
    if not sim:
        await asyncio.gather(stops_task, line_task, tap_task, validations_task) # Attende che tutti i task sia completati
    else:
        simulate_task = asyncio.create_task(simulate())
        await asyncio.gather(simulate_task, stops_task, line_task, tap_task, validations_task) # Attende che tutti i task sia completati


# Esegue il loop principale
asyncio.run(main())
