from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from pymongo import MongoClient
import datetime
from backend import config

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# MongoDB Connection
client = MongoClient(config.MONGO_URI)
db = client[config.DB_NAME]
locations_collection = db[config.COLLECTION_NAME]

# API Endpoint to receive GPS data (supports multiple devices)
@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.json
    device_id = data.get("device_id")  # Renamed vehicle_id to device_id
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if not all([device_id, latitude, longitude]):
        return jsonify({"error": "Missing data"}), 400

    location_data = {
        "device_id": device_id,
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": datetime.datetime.utcnow()
    }

    # Store in MongoDB
    locations_collection.insert_one(location_data)

    # Send real-time update for multiple devices
    socketio.emit('location_update', location_data)

    return jsonify({"message": "Location updated successfully!"}), 200

# API Endpoint to fetch past locations of a specific device
@app.route('/get_device_locations/<device_id>', methods=['GET'])
def get_device_locations(device_id):
    locations = list(locations_collection.find({"device_id": device_id}, {"_id": 0}))
    return jsonify({"device_id": device_id, "locations": locations})

# API to get the latest location of all devices
@app.route('/get_latest_locations', methods=['GET'])
def get_latest_locations():
    pipeline = [
        {"$sort": {"timestamp": -1}},
        {"$group": {
            "_id": "$device_id",
            "latest_latitude": {"$first": "$latitude"},
            "latest_longitude": {"$first": "$longitude"},
            "last_updated": {"$first": "$timestamp"}
        }},
        {"$project": {"device_id": "$_id", "_id": 0, "latest_latitude": 1, "latest_longitude": 1, "last_updated": 1}}
    ]

    latest_locations = list(locations_collection.aggregate(pipeline))
    return jsonify({"devices": latest_locations})

if __name__ != "__main__":
    gunicorn_app = app
