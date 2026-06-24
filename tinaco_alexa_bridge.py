```python
from flask import Flask, jsonify
import paho.mqtt.client as mqtt
import json
import threading
import time

#################################################
# CONFIG
#################################################

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "tinaco/+/status"

#################################################
# GLOBALS
#################################################

app = Flask(__name__)

devices = {}
mqtt_client = None

#################################################
# MQTT CALLBACKS
#################################################

def on_connect(client, userdata, flags, rc):

    print("MQTT CONNECTED RC =", rc)

    client.subscribe(MQTT_TOPIC)

    print("SUBSCRIBED TO:", MQTT_TOPIC)


def on_disconnect(client, userdata, rc):

    print("MQTT DISCONNECTED RC =", rc)


def on_message(client, userdata, msg):

    global devices

    try:

        print("TOPIC RX:", msg.topic)

        payload = json.loads(msg.payload.decode())

        device_id = payload.get("id", "").lower()

        devices[device_id] = payload

        devices[device_id]["server_time"] = int(time.time())

        print("MQTT UPDATE:", device_id)

    except Exception as e:

        print("MQTT ERROR:", e)

#################################################
# MQTT START
#################################################

def start_mqtt():

    global mqtt_client

    try:

        mqtt_client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1
        )

        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.on_disconnect = on_disconnect

        print("CONNECTING TO", MQTT_BROKER)

        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

        mqtt_client.loop_start()

        print("MQTT LOOP STARTED")

    except Exception as e:

        print("MQTT START ERROR:", e)

#################################################
# START MQTT THREAD
#################################################

mqtt_thread = threading.Thread(
    target=start_mqtt,
    daemon=True
)

mqtt_thread.start()

#################################################
# ROUTES
#################################################

@app.route("/")
def home():

    return "TINACO MQTT OK"


@app.route("/debug")
def debug():

    return jsonify(devices)


@app.route("/estado/<device_id>")
def estado(device_id):

    device_id = device_id.lower()

    if device_id not in devices:

        return jsonify({
            "ok": False,
            "msg": "device not found"
        })

    return jsonify(devices[device_id])


#################################################
# LOCAL TEST
#################################################

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=10000
    )
```
