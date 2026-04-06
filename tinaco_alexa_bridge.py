# -*- coding: utf-8 -*-

from flask import Flask,request,jsonify
import paho.mqtt.client as mqtt
import json
import time
import threading
import os
import requests

####################################
# CONFIG
####################################

MQTT_BROKER="broker.hivemq.com"
MQTT_TOPIC="tinaco/enrique/status"
DATA_FILE="last.json"

####################################
# TELEGRAM
####################################

TELEGRAM_ENABLED=False
TELEGRAM_TOKEN="TOKEN"
TELEGRAM_CHAT="CHAT"
TELEGRAM_COOLDOWN=30

####################################
# AWS ALEXA EVENTS
####################################

ALEXA_ENABLED=True
AWS_URL="https://vgnigchmrsauphzvmih2tqym5m0pphqe.lambda-url.us-east-1.on.aws/"
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

mqtt_ready=False
last_mqtt_time=0

last_data=None

data_lock=threading.Lock()

mqtt_started=False

last_pump_state=None

last_low_state=False
last_critical_state=False
last_full_state=False

last_alert_time=0
last_alexa_time=0

####################################
# APP
####################################

app=Flask(__name__)

####################################
# ALERT ENGINE
####################################

def alert_event(msg):

    print("EVENT:",msg)

    send_telegram(msg)

    send_alexa_event(msg)

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
# AWS EVENTS
####################################

def send_alexa_event(msg):

    global last_alexa_time

    if not ALEXA_ENABLED:
        return

    if time.time()-last_alexa_time < ALEXA_COOLDOWN:
        return

    try:
        payload={

        "type":"change",

        "level":norm["level"],

        "pump":norm["pump"]

                }
       

        requests.post(
            AWS_URL,
            json=payload,
            timeout=5
        )

        print("AWS event:",msg)

        last_alexa_time=time.time()

    except Exception as e:

        print("AWS error:",e)

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
    global mqtt_ready
    global last_mqtt_time

    try:

        raw=json.loads(msg.payload.decode())

        if "lvl" not in raw:
            return

        norm=normalize(raw)

        with data_lock:

            last_data=dict(norm)

            save_data(norm)

        mqtt_ready=True
        last_mqtt_time=time.time()

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

            alert_event("Tinaco lleno")

            last_full_state=True

        if level<98:

            last_full_state=False

####################################
# LOW
####################################

        if level<=LOW_LEVEL and not last_low_state:

            alert_event(f"Nivel bajo {level} por ciento")

            last_low_state=True

        if level>LOW_LEVEL+5:

            last_low_state=False

####################################
# CRITICAL
####################################

        if level<=CRITICAL_LEVEL and not last_critical_state:

            alert_event(f"Nivel crítico {level} por ciento")

            last_critical_state=True

        if level>CRITICAL_LEVEL+5:

            last_critical_state=False

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

def on_disconnect(client,userdata,rc):

    print("MQTT desconectado:",rc)

####################################
# MQTT LOOP (ROBUSTO)
####################################

def mqtt_loop():

    global last_mqtt_time

    while True:

        try:

            print("MQTT connecting")

            client=mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION1
            )

            client.on_connect=on_connect
            client.on_message=on_message
            client.on_disconnect=on_disconnect

            client.reconnect_delay_set(
                min_delay=1,
                max_delay=30
            )

            client.connect(
                MQTT_BROKER,
                1883,
                30
            )

            client.loop_start()

            while True:

                time.sleep(10)

                if last_mqtt_time!=0:

                    age=time.time()-last_mqtt_time

                    if age>120:

                        print("MQTT stale reconnect")

                        client.reconnect()

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

last_data=load_data()

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
# ROUTES
####################################

@app.route("/")
def home():

    return "Tinaco backend running"

@app.route("/health")
def health():

    return "OK"

@app.route("/debug")
def debug():

    return jsonify(get_state())

####################################
# ALEXA QUERY
####################################

@app.route("/alexa",methods=["POST"])
def alexa():

    state=get_state()

    if not state:

        speech="No tengo datos del tinaco"

    else:

        level=state["level"]
        liters=state["liters"]
        pump=state["pump"]

        speech=(

        f"El tinaco está al {level} por ciento. "
        f"Hay {liters} litros. "
        f"La bomba está {pump.lower()}"

        )

    return jsonify({

        "version":"1.0",

        "response":{

            "outputSpeech":{

                "type":"PlainText",

                "text":speech

            },

            "shouldEndSession":True

        }

    })

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
