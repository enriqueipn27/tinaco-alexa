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


def on_message(client,userdata,msg):

    global last_data
    global last_update

    try:

        data=json.loads(msg.payload.decode())

        if "level" not in data:
            return

        last_data=data

        last_update=time.time()

        print("MQTT:",data)

    except Exception as e:

        print("JSON error:",e)


def on_connect(client,userdata,flags,rc):

    print("MQTT conectado:",rc)

    client.subscribe(MQTT_TOPIC)

    print("Suscrito:",MQTT_TOPIC)


def mqtt_loop():

    client=mqtt.Client()

    client.on_connect=on_connect
    client.on_message=on_message

    print("Conectando MQTT")

    client.connect(MQTT_BROKER,1883,60)

    client.loop_forever()


def start_mqtt():

    thread=threading.Thread(target=mqtt_loop)

    thread.daemon=True

    thread.start()

    print("MQTT iniciado")


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


@app.route("/tinaco",methods=["POST","GET"])
def tinaco():

    global last_data

    try:

        # Obtener request Alexa seguro
        req=request.get_json(silent=True)

        if req is None:
            req={}

        req_type=req.get(
            "request",
            {}
        ).get(
            "type",
            ""
        )

        # LaunchRequest
        if req_type=="LaunchRequest":

            speech="Puedes preguntarme el nivel del tinaco"

        else:

            if last_data is None:

                speech="Esperando datos del tinaco"

            else:

                level=last_data.get("level",0)

                pump=last_data.get("pump","OFF")

                level_text=interpret_level(level)

                speech=f"Nivel {level} por ciento."

                speech+=f" Estado {level_text}."

                if pump=="ON":

                    speech+=" Bomba encendida."

                else:

                    speech+=" Bomba apagada."


        response=jsonify({

            "version":"1.0",

            "response":{

                "outputSpeech":{

                    "type":"PlainText",

                    "text":speech

                },

                "shouldEndSession":True

            }

        })

        # Importante para Alexa
        response.headers["Content-Type"]="application/json"

        return response,200


    except Exception as e:

        print("Error:",e)

        response=jsonify({

            "version":"1.0",

            "response":{

                "outputSpeech":{

                    "type":"PlainText",

                    "text":"Error"

                },

                "shouldEndSession":True

            }

        })

        response.headers["Content-Type"]="application/json"

        return response,200


if __name__=="__main__":

    app.run(

        host="0.0.0.0",

        port=int(os.environ.get("PORT",5000))

    )
