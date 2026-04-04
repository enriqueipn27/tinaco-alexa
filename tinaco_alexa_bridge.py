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

TELEGRAM_ENABLED=True

TELEGRAM_TOKEN="8771876521:AAHb-SxDYlQMt2BUm8TEzD7Epd5ViUQCHwk"

TELEGRAM_CHAT="8660553595"

MQTT_TIMEOUT=90
MQTT_OLD=300

####################################
# GLOBAL
####################################

last_data=None
data_lock=threading.Lock()

mqtt_started=False

last_pump_state=None

last_alert_time=0

test_sent=False

app=Flask(__name__)

####################################
# TELEGRAM
####################################

def send_telegram(msg):

    global last_alert_time

    if not TELEGRAM_ENABLED:
        return

    if time.time()-last_alert_time<10:
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

    return {

        "level":int(data.get("lvl",0)),

        "pump":"ON" if data.get("p",0)==1 else "OFF",

        "liters":int(data.get("l",0)),

        "height":float(data.get("h",0)),

        "wifi":int(data.get("w",-100)),

        "server_time":time.time()

    }

####################################
# MQTT
####################################

def on_message(client,userdata,msg):

    global last_data,last_pump_state,test_sent

    try:

        raw=json.loads(msg.payload.decode())

        if "lvl" not in raw:
            return

        norm=normalize(raw)

        with data_lock:

            last_data=dict(norm)

            save_data(norm)

        if not test_sent:

            send_telegram("Tinaco conectado ✅")

            test_sent=True

        pump=norm["pump"]

        if last_pump_state is None:
            last_pump_state=pump

        if pump!=last_pump_state:

            if pump=="ON":

                send_telegram(
                f"🚰 Bomba ENCENDIDA\nNivel {norm['level']}%"
                )

            else:

                send_telegram(
                f"✅ Tinaco LLENO\nNivel {norm['level']}%"
                )

            last_pump_state=pump

        if norm["level"]<20:

            send_telegram(
            f"⚠️ Nivel crítico {norm['level']}%"
            )

        if norm["wifi"]<-80:

            send_telegram(
            "📡 Señal WiFi débil"
            )

        print("MQTT:",norm)

    except Exception as e:

        print("MQTT error:",e)

def on_connect(client,userdata,flags,rc):

    if rc==0:

        print("MQTT conectado")

        client.subscribe(MQTT_TOPIC)

def mqtt_loop():

    while True:

        try:

            print("MQTT connecting")

            client=mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION1
            )

            client.on_connect=on_connect

            client.on_message=on_message

            client.connect(MQTT_BROKER,1883,60)

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
# SPEECH
####################################

def build_speech():

    data=get_state()

    if data is None:

        return "Sistema activo pero sin datos."

    elapsed=int(time.time()-data["server_time"])

    if elapsed<MQTT_TIMEOUT:

        time_text="Datos recientes."

    elif elapsed<MQTT_OLD:

        time_text="Datos válidos."

    else:

        time_text="Sin comunicación reciente."

        send_telegram(
        "⚠️ Tinaco sin comunicación"
        )

    speech="Estado del tinaco."

    speech+= " Bomba encendida." if data["pump"]=="ON" else " Bomba apagada."

    speech+=f" Nivel {data['level']} por ciento."

    speech+=f" Volumen {data['liters']} litros."

    speech+=f" Altura {round(data['height'],1)} centímetros."

    speech+=f" Señal wifi {data['wifi']} dBm."

    speech+=f" {time_text}"

    return speech

####################################
# ALEXA
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

    return "Tinaco Alexa bridge OK"

@app.route("/debug")
def debug():

    return jsonify(get_state())

@app.route("/tinaco",methods=["POST"])
def tinaco():

    return alexa_response(build_speech())

####################################
# MAIN
####################################

if __name__=="__main__":

    app.run(

        host="0.0.0.0",

        port=int(os.environ.get("PORT",5000))

    )
