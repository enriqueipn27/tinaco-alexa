from flask import Flask, request, jsonify, redirect
import paho.mqtt.client as mqtt
import json
import threading
import time
import uuid

app = Flask(__name__)

####################################
# CONFIG MQTT
####################################

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "tinaco/enrique/status"

####################################
# DATA GLOBAL
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
# OAUTH MEMORY STORE
####################################

auth_codes = {}
access_tokens = {}
refresh_tokens = {}

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
            "pump": "OFF",
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
# DEBUG DATA
####################################

@app.route("/debug")
def debug():
    return jsonify(last_data)

####################################
# AUTHORIZATION ENDPOINT
####################################

@app.route("/auth")
def auth():
    redirect_uri = request.args.get("redirect_uri")
    state = request.args.get("state")
    client_id = request.args.get("client_id")

    print("AUTH REQUEST:", redirect_uri, state, client_id)

    # generar código único por sesión
    auth_code = str(uuid.uuid4())

    auth_codes[auth_code] = {
        "client_id": client_id,
        "created": time.time(),
        "user": "enrique"
    }

    print("AUTH CODE GENERATED:", auth_code)

    return redirect(f"{redirect_uri}?state={state}&code={auth_code}")

####################################
# TOKEN ENDPOINT
####################################

@app.route("/token", methods=["POST"])
def token():
    grant_type = request.form.get("grant_type")
    code = request.form.get("code")
    refresh = request.form.get("refresh_token")
    client_id = request.form.get("client_id")

    print("TOKEN REQUEST:", grant_type, code, refresh, client_id)

    # intercambio normal auth code -> token
    if grant_type == "authorization_code":

        if code not in auth_codes:
            return jsonify({"error": "invalid_grant"}), 400

        access_token = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())

        access_tokens[access_token] = {
            "user": auth_codes[code]["user"],
            "created": time.time()
        }

        refresh_tokens[refresh_token] = {
            "user": auth_codes[code]["user"],
            "created": time.time()
        }

        print("TOKEN ISSUED:", access_token)

        return jsonify({
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 86400,
            "refresh_token": refresh_token
        })

    # renovación con refresh token
    elif grant_type == "refresh_token":

        if refresh not in refresh_tokens:
            return jsonify({"error": "invalid_refresh"}), 400

        new_access = str(uuid.uuid4())

        access_tokens[new_access] = {
            "user": refresh_tokens[refresh]["user"],
            "created": time.time()
        }

        print("TOKEN REFRESHED:", new_access)

        return jsonify({
            "access_token": new_access,
            "token_type": "Bearer",
            "expires_in": 86400,
            "refresh_token": refresh
        })

    return jsonify({"error": "unsupported_grant_type"}), 400

####################################
# ROOT
####################################

@app.route("/")
def home():
    return "FLOWYN backend activo"
