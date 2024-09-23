// Per avviare il server usare il comando node server.js
// server.js
// FUNZIONAMENTO: Il server si sottoscrite al topic router/gps al broker sull'indirizzo 192.168.1.80
const express = require('express');
const cors = require('cors');
const axios = require('axios'); 
const { exec } = require('child_process');  // Uso il modulo child_process di Node.js per eseguire lo script Python.
const mqtt = require('mqtt');   // Uso il modulo mqtt per gestire lo scambio di messaggi con il router

const app = express();
const port = 3000;

// Middleware per gestire richieste JSON
app.use(express.json());
// Configura CORS
app.use(cors());

// Endpoint per controllare lo stato del router
app.get('/check-router', async (req, res) => {  // effettua una get 
    const { routerIp } = req.query;

    if (!routerIp) {
        return res.status(400).json({ error: 'Devi fornire l\'IP del router come parametro della query.' });
    }

    try {
        const response = await axios.get(`http://${routerIp}/`, {
            timeout: 10000,  // Timeout dopo 5 secondi
        });
        
        // Se il router risponde, inviamo una risposta positiva©
        if (response.status >= 200 && response.status < 300) {
            res.json({ connected: true });
            console.log(response.status);
        } else {
            res.json({ connected: false });
            console.log(response.status);
        }
    } catch (error) {
        // In caso di errore (timeout, connessione rifiutata, ecc.), consideriamo il router non raggiungibile
        res.json({ connected: false });
        console.log(error);
    }
});

// Configura il client MQTT
const broker_url = 'mqtt://192.168.1.80' //'mqtt://172.20.10.3';   // Indirizzo del broker MQTT - secondo indirizzo (fuori casa)
const client = mqtt.connect(broker_url, {   // Connetti al broker MQTT con nome utente e password

    username: 'mqtt',  // Nome utente
    password: 'mqtt'   // Password
});
// Topic su cui ci si iscrive per i dati GPS
const topic_gps = 'router/gps';

let lastGpsData = null;  // Variabile per salvare gli ultimi dati GPS


// Quando il client si connette al broker
client.on('connect', () => {
    console.log('Connesso al broker MQTT');

    // Sottoscrivi al topic GPS
    client.subscribe(topic_gps, (err) => {
        if (!err) {
            console.log(`Sottoscritto al topic: ${topic_gps}`);
        } else {
            console.error(`Errore nella sottoscrizione: ${err}`);
        }
    });
});

/* TEST
const testMessage = '{"latitude": 45.4642, "longitude": 9.19}';
try {
    const testData = JSON.parse(testMessage);
    console.log('Test dati GPS:', testData);
} catch (error) {
    console.error('Errore nel parsing del test JSON:', error);
}
*/

client.on('message', (topic, message) => {
    const messageString = message.toString();  // Converti il messaggio in stringa
    console.log('Messaggio ricevuto:', messageString);  // Log del messaggio ricevuto
    
    try {
        // Parsa i dati GPS ricevuti (assumendo che sia in formato JSON)
        const parsedData = JSON.parse(messageString);
        
        // Verifica che i dati contengano latitude e longitude
        if (
            typeof parsedData.latitude === 'number' && 
            typeof parsedData.longitude === 'number'
        ) {
            lastGpsData = parsedData;
            console.log('Dati GPS ricevuti:', lastGpsData);
        } else {
            console.error('Dati GPS ricevuti non validi:', parsedData);
            lastGpsData = null;  // Rimuove i dati non validi
        }
    } catch (error) {
        console.error('Errore nel parsing dei dati GPS:', error);
        console.error('Messaggio problematico:', messageString);  // Log del messaggio problematico
        lastGpsData = null;  // Rimuove i dati non validi in caso di errore di parsing
    }
});

// Gestione degli errori nella connessione MQTT
client.on('error', (error) => {
    console.error('Errore nella connessione al broker MQTT:', error);
});

// Endpoint HTTP per rispondere con gli ultimi dati GPS
app.get('/get-gps', (req, res) => {
    if (lastGpsData) {
        // Se i dati GPS sono stati ricevuti e sono validi, restituiscili come risposta
        res.json(lastGpsData);
    } else {
        // Se non ci sono ancora dati GPS, restituisci un errore
        res.status(500).json({ error: 'Nessun dato GPS disponibile' });
    }
});
// Chiamata al programma python per il calcolo del nome della città dalle coordinate GPS
app.get('/get-city', async (req, res) => {
    const { latitude, longitude } = req.query;

    if (!latitude || !longitude) {
        return res.status(400).json({ error: 'Latitude and Longitude are required' });
    }
    console.log('Invio..');
    try {
        const response = await fetch(`http://localhost:8000/get-city?latitude=${latitude}&longitude=${longitude}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        res.json(data);
        console.log('Città inviata');
    } catch (error) {
        res.status(500).json({ error: 'Error fetching city data' });
        console.error('Errore nel calcolo della città');
    }
});

// Avvia il server HTTP
app.listen(port, () => {
    console.log(`Server in esecuzione su http://localhost:${port}`);
});