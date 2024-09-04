from lxml import etree
from datetime import datetime
import asyncio
import platform

from .config import file_params
from .file_opener import open_json


# Inizializza il root 
async def init_lxml():
    global ns, root
    params = open_json(1, file_params)
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


# Ripulisci il file params.json
async def clear_params():
    params = open_json(1, file_params)
    
    operator = search_all(root, "Operator")
    params["vector"] = search_elem(operator, "ShortName", "text")

    validation = search_all(root, "ValidBetween")[0]
    params["netex_file"]["valid_until"] = search_elem(validation, "ToDate", "text")
    params["netex_file"]["publication_timestamp"] = search_elem(root, "PublicationTimestamp", "text")

    params["position_rt"]["latitude"] = 0
    params["position_rt"]["longitude"] = 0

    params["buffer"]["nearby_stops_id"] = []
    params["buffer"]["count_divide"] = 1
    params["buffer"]["validazioni_raw"] = []

    params["infomobility"]["line_id"] = ""
    params["infomobility"]["journey"]["last_stop_time"] = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    params["infomobility"]["journey"]["stops"] = []

    params["validazioni"] = []
    
    open_json(0, file_params, params)
    await asyncio.sleep(params["repetition_wait_seconds"]["default"])