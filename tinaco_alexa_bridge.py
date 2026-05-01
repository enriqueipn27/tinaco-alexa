from flask import Flask, request, jsonify, redirect
import paho.mqtt.client as mqtt
import json
import threading
import time
import uuid
import os

app = Flask(__name__)

#################################################
# CONFIG MQTT
#################################################
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "tinaco/+/status"
STORE_FILE = "devices_store.json"

#################################################
# OAUTH CONFIG
#################################################
VALID_CLIENT_ID = "abc123"
VALID_CLIENT_SECRET = "tinaco2026secure"
VALID_SCOPE = "tinaco_control"

#################################################
# GLOBAL DATA
#################################################
devices = {}
auth_codes = {}
access_tokens = {}
refresh_tokens = {}
last_alerts = {}

#################################################
# LOAD / SAVE PERSISTENCE
#################################################
def load_store():
    global devices,last_alerts
    if os.path.exists(STORE_FILE):
        try:
            with open(STORE_FILE, "r") as f:
                pack = json.load(f)
                devices = pack.get("devices", {})
                last_alerts = pack.get("alerts", {})
            print("STORE LOADED")
        except Exception as e:
            print("STORE LOAD ERROR:", e)
            devices = {}
            last_alerts = {}

def save_store():
    try:
        with open(STORE_FILE, "w") as f:
            json.dump({"devices": devices, "alerts": last_alerts}, f)
    except Exception as e:
        print("STORE SAVE ERROR:", e)

load_store()

#################################################
# ALERT ENGINE
#################################################
def compute_alerts(device_id, data):
    level = data.get("level",0)
    overflow = data.get("overflow",0)
    age = int(time.time()) - data.get("server_time",0)

    low = level < 20
    critical = level < 10
    over = overflow == 1
    lost = age > 120
    stale = age > 30 and age <= 120
    fresh = age <= 30

    previous = last_alerts.get(device_id,{})

    recover = False
    if previous.get("low") and level >= 25:
        recover = True
    if previous.get("lost") and age <= 30:
        recover = True

    speech = "Sistema operando normalmente."

    if critical:
        speech = "Atención. El nivel de agua es crítico."
    elif low:
        speech = "Aviso. El nivel de agua está bajo."
    elif over:
        speech = "Atención. Se detecta posible derrame en el tinaco."
    elif lost:
        speech = "La comunicación con el sensor está demorada, pero conservo la última lectura disponible."
    elif stale:
        speech = "La última lectura está un poco retrasada, pero el sistema sigue monitoreando."
    elif recover:
        speech = "El sistema reporta recuperación a estado normal."

    last_alerts[device_id] = {
        "low": low,
        "critical": critical,
        "overflow": over,
        "lost": lost,
        "recover": recover
    }

    data["freshness"] = "FRESH" if fresh else "STALE" if stale else "LOST"
    data["alert_low"] = low
    data["alert_critical"] = critical
    data["alert_overflow"] = over
    data["alert_lost"] = lost
    data["alert_recover"] = recover
    data["speech"] = speech

    return data

#################################################
# MQTT CALLBACKS
#################################################
def on_connect(client, userdata, flags, rc):
    print("MQTT connected:", rc)
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    global devices
    try:
        payload = json.loads(msg.payload.decode())
        topic_parts = msg.topic.split("/")
        device_id = topic_parts[1].lower()

        devices[device_id] = {
            "device": device_id,
            "level": payload.get("lvl", 0),
            "height": payload.get("h", 0),
            "liters": payload.get("l", 0),
            "pump": payload.get("pump", "OFF"),
            "rssi": payload.get("r", 0),
            "flow": payload.get("f", 0),
            "freq": payload.get("fq", 0),
            "overflow": payload.get("ov", 0),
            "time": payload.get("ts", int(time.time())),
            "server_time": int(time.time())
        }

        compute_alerts(device_id, devices[device_id])
        save_store()
        print("MQTT UPDATE", device_id, devices[device_id])

    except Exception as e:
        print("MQTT ERROR:", e)

#################################################
# MQTT THREAD
#################################################
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

#################################################
# API DEVICE DATA
#################################################
@app.route('/api/<device_id>')
def api_device(device_id):
    device_id = device_id.lower()

    if device_id not in devices:
        return jsonify({
            "device": device_id,
            "status": "NO_DATA",
            "speech": "Todavía no tengo historial suficiente de este tinaco."
        })

    data = compute_alerts(device_id, devices[device_id])
    return jsonify(data)

#################################################
# DEBUG ALL
#################################################
@app.route('/debug')
def debug():
    out = {}
    for d in devices:
        out[d] = compute_alerts(d, devices[d])
    return jsonify(out)

#################################################
# OAUTH AUTH
#################################################
@app.route('/auth')
def auth():
    redirect_uri = request.args.get("redirect_uri")
    state = request.args.get("state")
    client_id = request.args.get("client_id")
    scope = request.args.get("scope")

    if client_id != VALID_CLIENT_ID or scope != VALID_SCOPE:
        return "unauthorized", 401

    auth_code = str(uuid.uuid4())
    auth_codes[auth_code] = {"client_id": client_id,"created": time.time(),"user": "enrique"}

    return redirect(f"{redirect_uri}?state={state}&code={auth_code}")

#################################################
# OAUTH TOKEN
#################################################
@app.route('/token', methods=['POST'])
def token():
    grant_type = request.form.get("grant_type")
    code = request.form.get("code")
    refresh = request.form.get("refresh_token")
    client_id = request.form.get("client_id")
    client_secret = request.form.get("client_secret")

    if client_id != VALID_CLIENT_ID or client_secret != VALID_CLIENT_SECRET:
        return jsonify({"error": "invalid_client"}), 401

    if grant_type == "authorization_code":
        if code not in auth_codes:
            return jsonify({"error": "invalid_grant"}), 400

        access_token = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        access_tokens[access_token] = {"user": "enrique", "created": time.time()}
        refresh_tokens[refresh_token] = {"user": "enrique", "created": time.time()}

        return jsonify({"access_token": access_token,"token_type": "Bearer","expires_in": 86400,"refresh_token": refresh_token})

    elif grant_type == "refresh_token":
        if refresh not in refresh_tokens:
            return jsonify({"error": "invalid_refresh"}), 400

        new_access = str(uuid.uuid4())
        access_tokens[new_access] = {"user": "enrique", "created": time.time()}

        return jsonify({"access_token": new_access,"token_type": "Bearer","expires_in": 86400,"refresh_token": refresh})

    return jsonify({"error": "unsupported_grant_type"}), 400

#################################################
# TOKEN VALIDATION
#################################################
@app.route('/validate')
def validate():
    token = request.args.get("token")

    if token in access_tokens:
        return jsonify({"valid": True, "user": access_tokens[token]["user"]})

    return jsonify({"valid": False}), 401

#################################################
# ROOT
#################################################
@app.route('/')
def home():
    return 'Mi Tinaco Render FailSoft V2.1 activo'

