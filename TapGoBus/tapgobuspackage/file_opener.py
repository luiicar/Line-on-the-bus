import json


# Apre il lettura o scrittura i file JSON
def open_json(mode, filename, data="", option=""):
    if mode: # 1 lettura
        with open(filename, "r") as file:
            data = json.load(file)
            return data
        
    else: # 0 scrittura
        with open(filename, "w") as file:
            if option == "clear":
                pass
            else:
                json.dump(data, file, indent=4)


