from flask import Flask, jsonify, request
import paho.mqtt.client as mqtt
import json
import threading
import time
import traceback
import requests
import os

#################################################
# CONFIG
#################################################

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

TOPIC_STATUS = "tinaco/+/status"
TOPIC_CONTROL = "calle/+/control"
#################################################
# GLOBALS
#################################################

app = Flask(__name__)
devices = {}
controls = {}
mqtt_client = None
last_B = None
last_fl = None
last_low55 = False

####################################################
TELEGRAM_TOKEN = "8771876521:AAGqVh5HsYn4KNES53DTTKnftKOuWMaRbnQ"

TELEGRAM_CHAT_ID = 8660553595
#################################################
#  telegram
#################################################
def send_telegram(msg):

    try:

        url = (
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
            f"/sendMessage"
        )

        r = requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": msg
            },
            timeout=10
        )

        print("TELEGRAM STATUS =", r.status_code)
        print("TELEGRAM RESPONSE =", r.text)

    except Exception as e:

        print("TELEGRAM ERROR:", e)


#################################################
# MQTT CALLBACKS
#################################################

def on_connect(client, userdata, flags, rc):

    print("MQTT CONNECTED RC =", rc)

    client.subscribe(TOPIC_STATUS)
    client.subscribe(TOPIC_CONTROL)

    print("SUBSCRIBED TO:", TOPIC_STATUS)
    print("SUBSCRIBED TO:", TOPIC_CONTROL)

def on_disconnect(client, userdata, rc):

    print("MQTT DISCONNECTED RC =", rc)

def on_message(client, userdata, msg):

    global devices
    global controls
    global last_B
    global last_fl
    global last_low55

    
    print("MQTT PID =", os.getpid())


    try:

        print("TOPIC RX:", msg.topic)

        payload = json.loads(msg.payload.decode())

        # tinaco/enrique/status
        if "/status" in msg.topic:

            device_id = payload.get("id","").lower()

            devices[device_id] = payload
            devices[device_id]["server_time"] = int(time.time())
              # SOLO ENRIQUE POR AHORA
            if device_id == "enrique":

                fl = payload.get("fl", 0)
                lvl = payload.get("lvl", 0)

                # Tinaco lleno
                if last_fl is not None:

                    if last_fl == 0 and fl == 1:
                        send_telegram(
                            f"✅ Tinaco Enrique lleno\n"
                            f"🚪 Flotador cerrado\n"
                            f"💧 {payload.get('l',0)} litros\n"
                            f"🌡️ {payload.get('t',0)} °C"
                        )


                last_fl = fl

                # Nivel bajo
                if lvl < 55:

                    if not last_low55:

                        send_telegram(
                            f"⚠️ Tinaco Enrique por debajo del 55%\n"
                            f"Nivel: {lvl}%\n"
                            f"Litros: {payload.get('l',0)}"
                        )

                        last_low55 = True

                else:

                    last_low55 = False

            print("STATUS UPDATE:", device_id)

        # calle/enrique/control
        elif "/control" in msg.topic:

            partes = msg.topic.split("/")

            if len(partes) >= 3:

                device_id = partes[1].lower()

                controls[device_id] = payload
                

                if device_id == "enrique":

                    B = payload.get("B", 0)

                    if last_B is not None:

                        if last_B == 0 and B == 1:

                            send_telegram(
                                "🔄 Bomba encendida"
                            )

                        elif last_B == 1 and B == 0:

                            send_telegram(
                                "⏹️ Bomba apagada"
                            )

                    last_B = B

                print("CONTROL UPDATE:", device_id, payload)

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



import os

@app.route("/debug")
def debug():

    return jsonify({
        "pid": os.getpid(),
        "devices_count": len(devices),
        "devices": list(devices.keys())
    })

@app.route("/telegram_test")
def telegram_test():

    send_telegram("🚰 Proyecto Tinaco conectado")

    return "TELEGRAM ENVIADO"

@app.route("/estado/<device_id>")
def estado(device_id):

    device_id = device_id.lower()

    if device_id not in devices:

        return jsonify({
            "ok": False,
            "msg": "device not found"
        })

    return jsonify(devices[device_id])

@app.route("/alexa_test/<device_id>")

def alexa_test(device_id):

    device_id = device_id.lower()

    if device_id not in devices:
        return "Aun no tengo datos del tinaco"

    d = devices[device_id]

    return (
        f"El tinaco esta al "
        f"{d.get('lvl',0)} por ciento, "
        f"con aproximadamente "
        f"{d.get('l',0)} litros. "
        f"La temperatura es "
        f"{d.get('t',0)} grados."
    )
#######################################
@app.route("/alexa", methods=["POST"])
def alexa():
    print("ALEXA PID =", os.getpid())
    print("ALEXA DEVICES =", devices)
    
    try:
        

        print("ALEXA REQUEST =", request.get_json())

        d = devices.get("enrique")

        if d is None:

            return jsonify({
                "version": "1.0",
                "response": {
                    "outputSpeech": {
                        "type": "PlainText",
                        "text": "Aún no tengo datos del tinaco."
                    },
                    "shouldEndSession": True
                }
            })

        c = controls.get("enrique", {})

        # Bomba
        if c.get("B", 0) == 1:
            bomba = "encendida"
        else:
            bomba = "apagada"

        # Válvula
        if c.get("V", 0) == 1:
            valvula = "abierta"
        else:
            valvula = "cerrada"

        # Flotador
        if d.get("fl", 0) == 1:
            flotador = "cerrado y el tinaco está lleno"
        else:
            flotador = "abierto"

        texto = (
            f"El tinaco está al "
            f"{d.get('lvl',0)} por ciento, "
            f"con aproximadamente "
            f"{d.get('l',0)} litros. "
            f"La temperatura es "
            f"{d.get('t',0)} grados. "
            f"La bomba está {bomba}. "
            f"La válvula está {valvula}. "
            f"El flotador está {flotador}."
        )

        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": texto
                },
                "shouldEndSession": True
            }
        })

    except Exception:

        print("========== ALEXA ERROR ==========")
        traceback.print_exc()
        print("=================================")

        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": "Ocurrió un error temporal."
                },
                "shouldEndSession": True
            }
        })
    

#################################################
# LOCAL TEST
#################################################

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=10000
    )


