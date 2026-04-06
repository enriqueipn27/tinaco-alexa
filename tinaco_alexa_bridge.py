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

AWS_URL="https://vgnigchmrsauphzvmih2tqym5m0pphqe.lambda-url.us-east-1.on.aws/"

ALEXA_COOLDOWN=15

LOW_LEVEL=20
CRITICAL_LEVEL=10
FULL_LEVEL=100

MQTT_TIMEOUT=180

####################################
# GLOBAL
####################################

last_data=None
last_sent=None

last_mqtt_time=0

last_pump_state=None

mqtt_started=False

data_lock=threading.Lock()

last_alexa_time=0

####################################
# APP
####################################

app=Flask(__name__)

####################################
# STORAGE
####################################

def save_data(data):

    try:

        with open(DATA_FILE,"w") as f:

            json.dump(data,f)

    except:

        pass

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

    return{

    "level":int(data.get("lvl",0)),

    "pump":"ON" if data.get("p",0)==1 else "OFF",

    "liters":int(data.get("l",0)),

    "height":float(data.get("h",0)),

    "wifi":int(data.get("w",-100)),

    "server_time":ts

    }

####################################
# SEND CHANGE REPORT
####################################

def send_change(data):

    global last_sent
    global last_alexa_time

    if data is None:
        return

    if time.time()-last_alexa_time < ALEXA_COOLDOWN:
        return

    if last_sent:

        if data["level"]==last_sent["level"] and data["pump"]==last_sent["pump"]:

            return

    try:

        payload={

        "type":"change",

        "level":data["level"],

        "pump":data["pump"]

        }

        requests.post(

            AWS_URL,

            json=payload,

            timeout=4

        )

        print("Alexa change:",payload)

        last_sent=dict(data)

        last_alexa_time=time.time()

    except Exception as e:

        print("Alexa error:",e)

####################################
# ALERT ENGINE
####################################

def alert_events(data):

    global last_pump_state

####################################
# PUMP CHANGE
####################################

    pump=data["pump"]

    if last_pump_state is None:

        last_pump_state=pump

    if pump!=last_pump_state:

        print("Pump change:",pump)

        send_change(data)

        last_pump_state=pump

####################################
# LEVEL EVENTS
####################################

    level=data["level"]

    if level<=LOW_LEVEL:

        print("Low level")

        send_change(data)

    if level<=CRITICAL_LEVEL:

        print("Critical level")

        send_change(data)

    if level>=FULL_LEVEL:

        print("Tank full")

        send_change(data)

####################################
# MQTT MESSAGE
####################################

def on_message(client,userdata,msg):

    global last_data
    global last_mqtt_time

    try:

        raw=json.loads(msg.payload.decode())

        if "lvl" not in raw:
            return

        norm=normalize(raw)

        with data_lock:

            last_data=dict(norm)

            save_data(norm)

        last_mqtt_time=time.time()

####################################
# SEND CHANGE
####################################

        send_change(norm)

####################################
# ALERT LOGIC
####################################

        alert_events(norm)

        print("MQTT:",norm)

    except Exception as e:

        print("MQTT error:",e)

####################################
# MQTT CONNECT
####################################

def on_connect(client,userdata,flags,rc):

    if rc==0:

        print("MQTT connected")

        client.subscribe(MQTT_TOPIC)

def on_disconnect(client,userdata,rc):

    print("MQTT disconnected")

####################################
# MQTT LOOP
####################################

def mqtt_loop():

    global last_mqtt_time

    while True:

        try:

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

####################################
# WATCHDOG
####################################

                if last_mqtt_time!=0:

                    age=time.time()-last_mqtt_time

                    if age>MQTT_TIMEOUT:

                        print("MQTT stale")

                        client.reconnect()

        except Exception as e:

            print("MQTT reconnect:",e)

            time.sleep(5)

####################################
# START MQTT
####################################

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
