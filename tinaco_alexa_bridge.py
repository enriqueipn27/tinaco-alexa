# -*- coding: utf-8 -*-

from flask import Flask,jsonify,request
import paho.mqtt.client as mqtt
import json
import time
import threading
import os

MQTT_BROKER="broker.hivemq.com"
MQTT_TOPIC="tinaco/enrique/status"

last_data=None
last_update=0
mqtt_started=False

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

    return "nivel critico"


def interpret_wifi(rssi):

    try:

        rssi=int(rssi)

        if rssi>=-60:
            return "señal wifi excelente"

        if rssi>=-70:
            return "señal wifi buena"

        if rssi>=-80:
            return "señal wifi regular"

        return "señal wifi débil"

    except:

        return ""


def build_speech():

    global last_data
    global last_update

    if last_data is None:

        return "Aún no recibo datos del tinaco"

    level=last_data.get("level",0)

    pump=last_data.get("pump","OFF")

    wifi=last_data.get("w",-100)

    level_text=interpret_level(level)

    wifi_text=interpret_wifi(wifi)

    age=int(time.time()-last_update)

    speech=f"Nivel {level} por ciento."

    speech+=f" Estado {level_text}."

    if pump=="ON":

        speech+=" Bomba encendida."

    else:

        speech+=" Bomba apagada."

    speech+=f" Última lectura hace {age} segundos."

    speech+=f" {wifi_text}."

    return speech


def on_message(client,userdata,msg):

    global last_data
    global last_update

    try:

        data=json.loads(msg.payload.decode())

        last_data=data

        last_update=time.time()

        print("MQTT recibido:",data)

    except Exception as e:

        print("JSON error:",e)


def on_connect(client,userdata,flags,rc):

    print("MQTT conectado:",rc)

    client.subscribe(MQTT_TOPIC)

    print("Suscrito a:",MQTT_TOPIC)


def mqtt_loop():

    while True:

        try:

            print("Intentando conectar MQTT...")

            client=mqtt.Client()

            client.on_connect=on_connect
            client.on_message=on_message

            client.connect(MQTT_BROKER,1883,60)

            client.loop_forever()

        except Exception as e:

            print("MQTT reconectando:",e)

            time.sleep(5)


def start_mqtt():

    global mqtt_started

    if mqtt_started:
        return

    mqtt_started=True

    thread=threading.Thread(target=mqtt_loop)

    thread.daemon=True

    thread.start()

    print("MQTT thread iniciado")


start_mqtt()


@app.route("/")
def home():

    return "Tinaco Alexa bridge running"


@app.route("/debug")
def debug():

    return jsonify({

        "last_data":last_data,

        "last_update":last_update

    })


@app.route("/tinaco",methods=["POST"])
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
