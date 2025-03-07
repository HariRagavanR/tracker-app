import tkinter as tk
from tkinter import ttk
import folium
import requests
import json
import threading
import webview
import websocket

# Backend URL
SERVER_URL = "https://my-tracker-app.onrender.com"
WS_URL = SERVER_URL.replace("https", "wss") + "/socket.io/"

class GPSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Live GPS Tracking")
        self.root.geometry("800x600")

        # Dropdown for selecting devices
        self.device_id_label = tk.Label(root, text="Select Device:")
        self.device_id_label.pack()
        self.device_id = ttk.Combobox(root)
        self.device_id.pack()

        # Button to load map
        self.load_map_btn = tk.Button(root, text="Load Map", command=self.load_map)
        self.load_map_btn.pack()

        # Start WebSocket listener in a separate thread
        threading.Thread(target=self.start_websocket, daemon=True).start()
        
        # Load devices from backend
        self.load_devices()

    def load_devices(self):
        response = requests.get(SERVER_URL + "/get_latest_locations")
        if response.status_code == 200:
            devices = response.json().get("devices", [])
            self.device_id["values"] = [device["device_id"] for device in devices]
            if devices:
                self.device_id.current(0)

    def load_map(self):
        selected_device = self.device_id.get()
        if not selected_device:
            return
        
        response = requests.get(f"{SERVER_URL}/get_device_locations/{selected_device}")
        if response.status_code == 200:
            locations = response.json().get("locations", [])
            if locations:
                latest = locations[-1]
                self.update_map(latest["latitude"], latest["longitude"])

    def update_map(self, lat, lon):
        folium_map = folium.Map(location=[lat, lon], zoom_start=15)
        folium.Marker([lat, lon], popup="Device Location").add_to(folium_map)
        
        # Save map as HTML
        map_file = "map.html"
        folium_map.save(map_file)
        
        # Open map in embedded browser in a separate thread
        threading.Thread(target=lambda: webview.create_window("Live Map", map_file), daemon=True).start()

    def start_websocket(self):
        def on_message(ws, message):
            data = json.loads(message)
            if "latitude" in data and "longitude" in data:
                self.update_map(data["latitude"], data["longitude"])

        ws = websocket.WebSocketApp(WS_URL, on_message=on_message)
        ws.run_forever()

if __name__ == "__main__":
    root = tk.Tk()
    app = GPSApp(root)
    root.mainloop()
