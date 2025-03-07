import eventlet
eventlet.monkey_patch()  # MUST BE FIRST

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS  # Added CORS support
from pymongo import MongoClient
import datetime
import os
from backend import config

# Flask App Setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "your_secret_key")
CORS(app)  # Enable CORS for mobile API access
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# MongoDB Connection
client = MongoClient(config.MONGO_URI)
db = client[config.DB_NAME]
locations_collection = db[config.COLLECTION_NAME]

# WebSocket Connection Handlers
@socketio.on('connect')
def handle_connect():
    print("A client connected.")

@socketio.on('disconnect')
def handle_disconnect():
    print("A client disconnected.")

# API Endpoint to receive GPS data (supports multiple devices)
@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.json
    device_id = data.get("device_id")
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if not all([device_id, latitude, longitude]):
        return jsonify({"error": "Missing data"}), 400

    location_data = {
        "device_id": device_id,
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": datetime.datetime.utcnow().isoformat()  # Store timestamp in ISO format
    }

    with app.app_context():  # Ensuring DB operation runs in app context
        locations_collection.insert_one(location_data)

    # Send real-time update for multiple devices
    socketio.emit('location_update', location_data)

    return jsonify({"message": "Location updated successfully!"}), 200

# API Endpoint to fetch past locations of a specific device
@app.route('/get_device_locations/<device_id>', methods=['GET'])
def get_device_locations(device_id):
    with app.app_context():
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

    with app.app_context():
        latest_locations = list(locations_collection.aggregate(pipeline))

    return jsonify({"devices": latest_locations})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
