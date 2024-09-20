from lxml import etree
from datetime import datetime
import asyncio
import pandas as pd

from .config import file_params, file_buffer
from .file_opener import open_json


# Effettua il parser del file lxml
async def init_lxml():
    global ns, root
    params = open_json(1, file_params)
    netex = params["netex_file"]["path"] + params["netex_file"]["name"]
    ns = {'ns': params["netex_file"]["namespace"]}
    root = etree.parse(netex) # Carica il file XML
    await asyncio.sleep(params["await_seconds"]["default"])


# Ritorna la variabile root
def get_root():
    return root


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
    elems = node.xpath(f".//ns:{path}", namespaces=ns)
    if len(elems) == 1:
        return elems[0]
    else:
        return elems


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


# Effettua il parser del file excel
async def init_pd():
    global df
    params = open_json(1, file_params)
    excel = params["excel_file"]["path"] + params["excel_file"]["name"]
    df = pd.read_excel(excel)
    await asyncio.sleep(params["await_seconds"]["default"])


# Cerca il comune nel DataFrame e restituisci l'ID corrispondente
def get_code_svr(nome_comune):
    comune = df[df["COMUNE"].str.upper() == nome_comune.upper()]
    if not comune.empty:
        return int(comune.iloc[0]["COD_SVR"])
    else:
        return None


# Inizializza tutti i file json
async def init_database():
    # params.json
    params = open_json(1, file_params)
    
    operator = search_all(root, "Operator")
    params["vector"] = search_elem(operator, "ShortName", "text")

    validation = search_all(root, "ValidBetween")[0]
    params["netex_file"]["valid_until"] = search_elem(validation, "ToDate", "text")
    params["netex_file"]["publication_timestamp"] = search_elem(root, "PublicationTimestamp", "text")

    open_json(0, file_params, params)

    # buffer.json
    buffer = open_json(1, file_buffer)

    buffer["position_rt"]["latitude"] = 0
    buffer["position_rt"]["longitude"] = 0

    buffer["line_id"] = ""
    buffer["journey"]["last_stop_time"] = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    buffer["journey"]["stops"] = []

    buffer["nearby_stops_id"] = []
    buffer["validazioni_raw"] = []
    buffer["validazioni"] = []
    
    open_json(0, file_buffer, buffer)

    await asyncio.sleep(params["await_seconds"]["default"])
