from flask import Flask, request, jsonify, redirect
import paho.mqtt.client as mqtt
import json
import threading
import time

app = Flask(__name__)

####################################
# CONFIG MQTT
####################################

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "tinaco/enrique/status"

####################################
# DATA GLOBAL (último estado)
####################################

last_data = {
    "level": 0,
    "height": 0,
    "liters": 0,
    "pump": "OFF",
    "rssi": 0,
    "time": 0
}

####################################
# MQTT CALLBACK
####################################

def on_connect(client, userdata, flags, rc):
    print("MQTT connected:", rc)
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    global last_data
    try:
        payload = json.loads(msg.payload.decode())
        
        last_data = {
            "level": payload.get("lvl", 0),
            "height": payload.get("h", 0),
            "liters": payload.get("l", 0),
            "pump": "OFF",  # temporal (no usamos bomba aún)
            "rssi": payload.get("r", 0),
            "time": payload.get("ts", 0)
        }

        print("MQTT UPDATE:", last_data)

    except Exception as e:
        print("MQTT ERROR:", e)

####################################
# MQTT THREAD
####################################

def mqtt_loop():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    while True:
        try:
            print("Connecting MQTT...")
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_forever()
        except Exception as e:
            print("MQTT reconnect:", e)
            time.sleep(5)

threading.Thread(target=mqtt_loop, daemon=True).start()

####################################
# DEBUG (Alexa usa esto)
####################################

@app.route("/debug")
def debug():
    return jsonify(last_data)

####################################
# AUTH (FIXED OAuth)
####################################

@app.route("/auth")
def auth():
    redirect_uri = request.args.get("redirect_uri")
    state = request.args.get("state")

    print("AUTH REQUEST:", redirect_uri, state)

    # 🔥 ya no usamos códigos absurdos
    return redirect(f"{redirect_uri}?state={state}&code=FLOWYN_OK")

####################################
# TOKEN
####################################

@app.route("/token", methods=["POST"])
def token():
    return jsonify({
        "access_token": "flowyn-token",
        "token_type": "Bearer",
        "expires_in": 3600
    })

####################################
# ROOT (opcional)
####################################

@app.route("/")
def home():
    return "FLOWYN backend activo"
