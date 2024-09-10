# Il codice invia al broker in qos=2 ogni 10s un messaggio contenente i dati di longitudine e latitudine
import paho.mqtt.client as mqtt
import time
import json
import random 

# Configurazione broker MQTT
broker_address = "192.168.1.80"  # IP del broker MQTT
broker_port = 1883
mqtt_topic = "router/gps"  # Topic su cui pubblicare i dati GPS
mqtt_username = "mqtt"  # Username per l'autenticazione
mqtt_password = "mqtt"  # Password per l'autenticazione

# Simulazione di una funzione per ottenere dati GPS direttamente (ad esempio da un'API locale del router)
current_latitude = 45.4642
current_longitude = 9.1900

def get_gps_data():
    global current_latitude, current_longitude
    
    # Incrementa le coordinate (puoi personalizzare l'incremento)
    current_latitude += random.uniform(-0.01, 0.01)  # Incremento casuale
    current_longitude += random.uniform(-0.01, 0.01)  # Incremento casuale
    
    # Assicurati che le coordinate rimangano nei limiti validi
    current_latitude = max(min(current_latitude, 90.0), -90.0)
    current_longitude = max(min(current_longitude, 180.0), -180.0)
    
    return {"latitude": current_latitude, "longitude": current_longitude}

# Funzione di callback per la connessione
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connesso con successo al broker MQTT")
    else:
        print(f"Connessione fallita. Codice errore: {rc}")

# Funzione di callback per la pubblicazione
def on_publish(client, userdata, mid):
    print(f"Messaggio pubblicato con ID: {mid}")

# Configura il client MQTT
client = mqtt.Client()
client.username_pw_set(mqtt_username, mqtt_password)  # Imposta username e password
client.on_connect = on_connect
client.on_publish = on_publish

# Connetti al broker e avvia il loop asincrono
client.connect(broker_address, broker_port, 60)
client.loop_start()  # Avvia il loop per gestire le connessioni asincrone

def publish_gps():
    gps_data = get_gps_data()
    result = client.publish(mqtt_topic, json.dumps(gps_data), qos=2)
    status = result.rc

    if status == 0:
        print(f"Messaggio pubblicato con successo: {gps_data}")
    else:
        print(f"Errore nella pubblicazione. Codice: {status}")

# Pubblicazione periodica (ogni 10 secondi)
try:
    while True:
        publish_gps()
        time.sleep(10)
except KeyboardInterrupt:
    print("Interruzione manuale...")
finally:
    client.loop_stop()  # Interrompi il loop in modo sicuro
    client.disconnect()  # Disconnetti in modo sicuro
