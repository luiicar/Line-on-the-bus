from geopy.geocoders import Nominatim
from flask import Flask, jsonify, request

app = Flask(__name__)

geolocator = Nominatim(user_agent="openstreetmap.org")

@app.route('/get-city', methods=['GET'])
def get_city():
    print("Richiesta ricevuta!")
    latitude = request.args.get('latitude')
    longitude = request.args.get('longitude')
    print("Calcolo...")

    if not latitude or not longitude:
        return jsonify({'error': 'Latitude and Longitude are required'}), 400

    try:
        location = geolocator.reverse((latitude, longitude), language='it')
        print(location)

        if location and location.raw:
            address = location.raw.get('address', {})
            comune =   address.get('town') or address.get('city') or address.get('village')
            return jsonify({'city': comune})
        else:
            return jsonify({'error': 'Location not found'}), 404
    except Exception as e:
        print(f"Errore: {e}")
        return jsonify({'error': 'An error occurred while processing the request'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
