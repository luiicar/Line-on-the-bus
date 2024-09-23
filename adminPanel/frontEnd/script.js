

// Script per la main page
let intervalId = null;

function checkAuth() {
    console.log('Controllo delle credenziali in corso...');
    if (localStorage.getItem('authenticated') !== 'true') {
        window.location.href = "login.html";
    }
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded event fired');
    if (document.querySelector('[data-page="mainPage"]')) { 
        checkAuth();
        console.log('daje');
        document.querySelector('.router-section').style.display = 'none';

        // Inizializza la mappa
        var map = L.map('map').setView([40.85, 14.26], 10); // Imposta un centro e zoom di default

        // Aggiungi il layer di OpenStreetMap
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        // Aggiungi un marker alla mappa
        var marker;

        // Funzione per aggiornare la mappa con la posizione GPS
        function updateMap(lat, lon) {
            map.setView([lat, lon], 13); // Aggiorna la vista della mappa alla nuova posizione
            if (marker) {
                marker.remove(); // Se esiste già un marker, rimuovilo
            }
            // Aggiungi un nuovo marker alla nuova posizione
            marker = L.marker([lat, lon]).addTo(map)
                .bindPopup(`Latitude: ${lat}, Longitude: ${lon}`).openPopup();
        }

        // Funzione per gestire la richiesta dei dati GPS al server Node.js
        function getGPSdata() {
            fetch('http://localhost:3000/get-gps')
                .then(response => response.json())
                .then(data => {
                    if (data.latitude && data.longitude) {
                        document.getElementById('gpsResult').textContent = 
                            `Latitudine: ${data.latitude}, Longitudine: ${data.longitude}`;
                        updateMap(data.latitude, data.longitude); // Aggiorna la mappa
                        return fetch(`http://localhost:3000/get-city?latitude=${data.latitude}&longitude=${data.longitude}`);
                    } else {
                        document.getElementById('gpsResult').textContent = 'No GPS data available';
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.city) {
                        document.getElementById('cityResult').textContent = `Place: ${data.city}`;
                    } else {
                        document.getElementById('cityResult').textContent = 'Place not found';
                    }
                })
                .catch(error => {
                    console.error('Request error:', error);
                    document.getElementById('gpsResult').textContent = 'Request error';
                });
        }

        document.getElementById('getGPSButton').addEventListener('click', function() {
            getGPSdata();
        });
    }
});


function logout() {
    localStorage.removeItem('authenticated');
    window.location.href = "login.html";
}

function checkRouterStatus(ip) {
    const statusCircle = document.getElementById("status-circle");
    const connectionStatus = document.getElementById("connection-status");
    const statusTime = document.getElementById("status-time");

    console.log(`Controllo stato del router all'indirizzo ${ip}...`);
    statusCircle.style.backgroundColor = 'orange';
    connectionStatus.innerText = 'Controllando...';

    setTimeout(() => {
        const isConnected = Math.random() > 0.2;
        if (isConnected) {
            statusCircle.style.backgroundColor = 'green';
            connectionStatus.innerText = 'Connected';
        } else {
            statusCircle.style.backgroundColor = 'red';
            connectionStatus.innerText = 'Disconnected';
        }
        const currentTime = new Date().toLocaleTimeString();
        statusTime.innerText = `Last check: ${currentTime}`;
    }, 2000);
}

function showRouterSection(busTitle) {
    document.querySelector('.router-section').style.display = 'flex';
    document.querySelector('.right-section').style.display = 'none';
    document.getElementById('titleSection').textContent = busTitle;
}

function showRightSection() {
    document.querySelector('.right-section').style.display = 'block';
    document.querySelector('.router-section').style.display = 'none';
}

// Funzione per la lettura della linea del bus, questa informazione andrebbe, nella fase successiva, letta direttamente dal router tramite il broker
function checkBusLine() {
    const busLineElement = document.getElementById('busLine');
    busLineElement.innerText = 'Line: ' + (Math.floor(Math.random() * 10) + 1);
}

document.getElementById('getGPSButton').addEventListener('click', function() {
    const gpsResult = document.getElementById('gpsResult');
    const lat = (Math.random() * 180 - 90).toFixed(6);
    const lon = (Math.random() * 360 - 180).toFixed(6);

    gpsResult.innerText = `Latitude: ${lat}, Longitude: ${lon}`;

    var map = L.map('map').setView([lat, lon], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    L.marker([lat, lon]).addTo(map)
        .bindPopup('Bus is here!')
        .openPopup();
});


// Controllo Protocollo - Dominio - Porta 
console.log('Protocollo:', window.location.protocol);
console.log('Dominio:', window.location.hostname);
console.log('Porta:', window.location.port);
