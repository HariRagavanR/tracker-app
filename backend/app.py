from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from pymongo import MongoClient
import datetime
import config

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# MongoDB Connection
client = MongoClient(config.MONGO_URI)
db = client[config.DB_NAME]
locations_collection = db[config.COLLECTION_NAME]

# API Endpoint to receive GPS data
@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.json
    vehicle_id = data.get("vehicle_id")
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if not all([vehicle_id, latitude, longitude]):
        return jsonify({"error": "Missing data"}), 400

    location_data = {
        "vehicle_id": vehicle_id,
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": datetime.datetime.utcnow()
    }

    locations_collection.insert_one(location_data)

    # Send real-time update to the frontend
    socketio.emit('location_update', location_data)

    return jsonify({"message": "Location updated successfully!"}), 200

# API Endpoint to fetch past locations of a vehicle
@app.route('/get_locations/<vehicle_id>', methods=['GET'])
def get_locations(vehicle_id):
    locations = list(locations_collection.find({"vehicle_id": vehicle_id}, {"_id": 0}))
    return jsonify({"vehicle_id": vehicle_id, "locations": locations})

if __name__ != "__main__":
    gunicorn_app = app
