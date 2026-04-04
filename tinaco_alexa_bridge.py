# -*- coding: utf-8 -*-

from flask import Flask,request,jsonify
import paho.mqtt.client as mqtt
import json
import time
import threading
import os
import requests

from datetime import datetime
from zoneinfo import ZoneInfo

####################################
# CONFIG
####################################

MQTT_BROKER="broker.hivemq.com"

MQTT_TOPIC="tinaco/enrique/status"

DATA_FILE="last.json"

####################################
# TELEGRAM
####################################

TELEGRAM_ENABLED=True

TELEGRAM_TOKEN="TU_TOKEN"

TELEGRAM_CHAT="TU_CHAT"

TELEGRAM_COOLDOWN=10

####################################
# ALEXA EVENTS
####################################

ALEXA_ENABLED=True

# mismo backend (loop interno)
ALEXA_EVENT_URL="https://TU_RENDER_URL/alexa_event"

ALEXA_COOLDOWN=20

####################################
# LIMITS
####################################

LOW_LEVEL=20

CRITICAL_LEVEL=10

FULL_LEVEL=100

####################################
# GLOBAL
####################################

last_data=None

data_lock=threading.Lock()

mqtt_started=False

last_pump_state=None

last_low_state=False

last_critical_state=False

last_full_state=False

last_alert_time=0

last_alexa_time=0

test_sent=False

####################################
# APP
####################################

app=Flask(__name__)

####################################
# CENTRAL EVENT ENGINE
####################################

def alert_event(msg):

    print("EVENT:",msg)

    send_telegram(msg)

    send_alexa(msg)

####################################
# TELEGRAM
####################################

def send_telegram(msg):

    global last_alert_time

    if not TELEGRAM_ENABLED:
        return

    if time.time()-last_alert_time < TELEGRAM_COOLDOWN:
        return

    try:

        url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

        requests.get(

            url,

            params={

                "chat_id":TELEGRAM_CHAT,

                "text":msg

            },

            timeout=5

        )

        last_alert_time=time.time()

    except Exception as e:

        print("Telegram error:",e)

####################################
# ALEXA EVENTS
####################################

def send_alexa(msg):

    global last_alexa_time

    if not ALEXA_ENABLED:
        return

    if time.time()-last_alexa_time < ALEXA_COOLDOWN:
        return

    try:

        requests.post(

            ALEXA_EVENT_URL,

            json={

                "message":msg

            },

            timeout=5

        )

        last_alexa_time=time.time()

    except Exception as e:

        print("Alexa error:",e)

####################################
# STORAGE
####################################

def save_data(data):

    try:

        with open(DATA_FILE,"w") as f:

            json.dump(data,f)

    except Exception as e:

        print("Save error:",e)

def load_data():

    try:

        with open(DATA_FILE) as f:

            return json.load(f)

    except:

        return None

####################################
# NORMALIZE
####################################

def normalize(data):

    ts=data.get("ts")

    if ts is None:

        ts=time.time()

    return {

        "level":int(data.get("lvl",0)),

        "pump":"ON" if data.get("p",0)==1 else "OFF",

        "liters":int(data.get("l",0)),

        "height":float(data.get("h",0)),

        "wifi":int(data.get("w",-100)),

        "server_time":ts

    }

####################################
# MQTT MESSAGE
####################################

def on_message(client,userdata,msg):

    global last_data
    global last_pump_state
    global last_low_state
    global last_critical_state
    global last_full_state
    global test_sent

    try:

        raw=json.loads(msg.payload.decode())

        if "lvl" not in raw:
            return

        norm=normalize(raw)

        with data_lock:

            last_data=dict(norm)

            save_data(norm)

####################################
# FIRST CONNECT
####################################

        if not test_sent:

            alert_event("Sistema tinaco conectado")

            test_sent=True

####################################
# PUMP EVENTS
####################################

        pump=norm["pump"]

        if last_pump_state is None:

            last_pump_state=pump

        if pump!=last_pump_state:

            if pump=="ON":

                alert_event(

                f"Bomba encendida. Nivel {norm['level']} por ciento"

                )

            else:

                alert_event(

                f"Bomba apagada. Nivel {norm['level']} por ciento"

                )

            last_pump_state=pump

####################################
# LEVEL EVENTS
####################################

        level=norm["level"]

####################################
# FULL
####################################

        if level>=FULL_LEVEL and not last_full_state:

            alert_event(

            "Tinaco lleno"

            )

            last_full_state=True

        if level<98:

            last_full_state=False

####################################
# LOW
####################################

        if level<=LOW_LEVEL and not last_low_state:

            alert_event(

            f"Nivel bajo {level} por ciento"

            )

            last_low_state=True

        if level>LOW_LEVEL+5:

            last_low_state=False

####################################
# CRITICAL
####################################

        if level<=CRITICAL_LEVEL and not last_critical_state:

            alert_event(

            f"Nivel crítico {level} por ciento"

            )

            last_critical_state=True

        if level>CRITICAL_LEVEL+5:

            last_critical_state=False

####################################
# WIFI EVENT
####################################

        if norm["wifi"]<-80:

            alert_event(

            "Señal WiFi débil"

            )

        print("MQTT:",norm)

    except Exception as e:

        print("MQTT error:",e)

####################################
# MQTT CONNECT
####################################

def on_connect(client,userdata,flags,rc):

    if rc==0:

        print("MQTT conectado")

        client.subscribe(MQTT_TOPIC)

####################################
# MQTT LOOP
####################################

def mqtt_loop():

    while True:

        try:

            print("MQTT connecting")

            client=mqtt.Client(

                mqtt.CallbackAPIVersion.VERSION1

            )

            client.on_connect=on_connect

            client.on_message=on_message

            client.connect(

                MQTT_BROKER,

                1883,

                60

            )

            client.loop_forever()

        except Exception as e:

            print("MQTT reconnect:",e)

            time.sleep(5)

def start_mqtt():

    global mqtt_started

    if mqtt_started:
        return

    mqtt_started=True

    thread=threading.Thread(

        target=mqtt_loop,

        daemon=True

    )

    thread.start()

start_mqtt()

####################################
# STATE
####################################

def get_state():

    global last_data

    with data_lock:

        if last_data:

            return dict(last_data)

    data=load_data()

    if data:

        last_data=data

        return dict(data)

    return None

####################################
# SPEECH BUILDER
####################################

def build_speech():

    data=get_state()

    if data is None:

        return "Sistema activo sin datos"

    elapsed=int(time.time()-data["server_time"])

    if elapsed<45:

        state="Sistema normal"

    elif elapsed<90:

        state="Sistema atrasado"

    else:

        state="Sistema sin comunicación"

####################################
# TIME
####################################

    local_time=datetime.fromtimestamp(

        data["server_time"],

        ZoneInfo("America/Mexico_City")

    )

    hour=local_time.strftime("%H:%M")

####################################
# SPEECH
####################################

    speech="Estado del tinaco."

    speech+= " Bomba encendida." if data["pump"]=="ON" else " Bomba apagada."

    speech+=f" Nivel {data['level']} por ciento."

    speech+=f" Volumen {data['liters']} litros."

    speech+=f" Medido a las {hour}."

    speech+=f" {state}"

    return speech

####################################
# ALEXA RESPONSE
####################################

def alexa_response(text):

    return {

        "version":"1.0",

        "response":{

            "outputSpeech":{

                "type":"PlainText",

                "text":text

            },

            "shouldEndSession":True

        }

    }

####################################
# ROUTES
####################################

@app.route("/")

def home():

    return "Tinaco backend OK"

@app.route("/debug")

def debug():

    return jsonify(get_state())

@app.route("/tinaco",methods=["POST"])

def tinaco():

    return alexa_response(build_speech())

####################################
# ALEXA EVENT ENDPOINT
####################################

@app.route("/alexa_event",methods=["POST"])

def alexa_event():

    data=request.json

    msg=data.get("message","Alerta tinaco")

    print("Alexa trigger:",msg)

    return {"ok":True}

####################################
# MAIN
####################################

if __name__=="__main__":

    app.run(

        host="0.0.0.0",

        port=int(

            os.environ.get("PORT",5000)

        )

    )
