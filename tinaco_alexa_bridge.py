# -*- coding: utf-8 -*-

from flask import Flask,jsonify,request
import paho.mqtt.client as mqtt
import json
import time
import threading
import os

MQTT_BROKER="broker.hivemq.com"
MQTT_TOPIC="tinaco/enrique/status"

DATA_FILE="last.json"

last_data=None
last_update=0

app=Flask(__name__)


def interpret_level(level):

    if level>=80:
        return "casi lleno"

    if level>=60:
        return "nivel alto"

    if level>=40:
        return "nivel medio"

    if level>=20:
        return "nivel bajo"

    return "nivel crítico"


def interpret_wifi(w):

    if w>=-60:
        return "señal wifi excelente"

    if w>=-70:
        return "señal wifi buena"

    if w>=-80:
        return "señal wifi regular"

    return "señal wifi débil"


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


def on_message(client,userdata,msg):

    global last_data
    global last_update

    try:

        data=json.loads(msg.payload.decode())

        if "level" not in data:
            return

        last_data=data
        last_update=time.time()

        save_data(data)

        print("MQTT:",data)

    except Exception as e:

        print("JSON error:",e)


def on_connect(client,userdata,flags,rc):

    if rc==0:

        print("MQTT conectado")

        client.subscribe(MQTT_TOPIC)


def start_mqtt():

    def run():

        while True:

            try:

                print("MQTT connecting")

                client=mqtt.Client()

                client.on_connect=on_connect
                client.on_message=on_message

                client.connect(MQTT_BROKER,1883,60)

                client.loop_forever()

            except Exception as e:

                print("MQTT reconnect",e)

                time.sleep(5)

    thread=threading.Thread(target=run)

    thread.daemon=True

    thread.start()

    print("MQTT iniciado")


start_mqtt()


@app.route("/")
def home():

    return "Tinaco Alexa bridge running"


@app.route("/debug")
def debug():

    data=last_data

    if data is None:

        data=load_data()

    return jsonify({

        "last_data":data,
        "last_update":last_update

    })


def build_speech():

    global last_data
    global last_update

    if last_data is None:

        last_data=load_data()

        if last_data is None:

            return "Aún no recibo datos del tinaco"

    level=last_data.get("level",0)
    pump=last_data.get("pump","OFF")
    wifi=last_data.get("w",-100)

    level_text=interpret_level(level)
    wifi_text=interpret_wifi(wifi)

    # TIEMPO REAL CORRECTO
    elapsed=int(time.time()-last_update)

    if elapsed<90:

        time_text=f"Última lectura hace {elapsed} segundos."

    else:

        mins=int(elapsed/60)

        time_text=f"Última lectura hace {mins} minutos."


    speech=f"Nivel {level} por ciento."
    speech+=f" Estado {level_text}."
    speech+=f" {time_text}"
    speech+=f" {wifi_text}."

    if pump=="ON":

        speech+=" Bomba encendida."

    else:

        speech+=" Bomba apagada."

    return speech


@app.route("/tinaco",methods=["POST","GET"])
def tinaco():

    try:

        req=request.get_json(force=True)

        print("Alexa:",req)

        speech=build_speech()

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

    except Exception as e:

        print("Error:",e)

        return jsonify({

            "version":"1.0",

            "response":{

                "outputSpeech":{

                    "type":"PlainText",

                    "text":"Error interno"

                },

                "shouldEndSession":True

            }

        })


if __name__=="__main__":

    app.run(

        host="0.0.0.0",
        port=int(os.environ.get("PORT",5000))

    )
