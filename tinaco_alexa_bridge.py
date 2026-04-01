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


def on_message(client,userdata,msg):

    global last_data
    global last_update

    try:

        data=json.loads(msg.payload.decode())

        if "level" not in data:
            return

        last_data=data

        last_update=time.time()

        print("MQTT recibido:",data)

    except Exception as e:

        print("JSON error:",e)


def on_connect(client,userdata,flags,rc):

    print("MQTT conectado codigo:",rc)

    if rc==0:

        client.subscribe(MQTT_TOPIC)

        print("Suscrito a:",MQTT_TOPIC)


def mqtt_loop():

    while True:

        try:

            print("Intentando conectar MQTT...")

            client=mqtt.Client(
                protocol=mqtt.MQTTv311
            )

            client.on_connect=on_connect
            client.on_message=on_message

            client.connect(
                MQTT_BROKER,
                1883,
                60
            )

            client.loop_start()

            while True:

                time.sleep(30)

        except Exception as e:

            print("MQTT reconectando:",e)

            time.sleep(5)


def start_mqtt():

    global mqtt_started

    if mqtt_started:
        return

    mqtt_started=True

    thread=threading.Thread(
        target=mqtt_loop
    )

    thread.daemon=True

    thread.start()

    print("MQTT thread iniciado")


# iniciar MQTT al arrancar worker
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
    global last_update

    try:

        # GET debug manual
        if request.method=="GET":

            return jsonify({

                "status":"running",

                "last_data":last_data,

                "last_update":last_update

            })

        # POST Alexa (seguro)
        req=request.get_json(silent=True)

        if req is None:
            req={}

        print("Alexa request:",req)

        req_type=req.get(
            "request",
            {}
        ).get(
            "type",
            ""
        )

        # Launch skill
        if req_type=="LaunchRequest":

            speech="Puedes preguntarme el nivel del tinaco"

        # Intent
        elif req_type=="IntentRequest":

            intent=req.get(
                "request",
                {}
            ).get(
                "intent",
                {}
            ).get(
                "name",
                ""
            )

            print("Intent:",intent)

            if last_data is None:

                speech="Aun no recibo datos del tinaco"

            else:

                level=last_data.get("level",0)

                pump=last_data.get("pump","OFF")

                level_text=interpret_level(level)

                speech=f"El nivel del tinaco es {level} por ciento."

                speech+=f" Estado {level_text}."

                if pump=="ON":

                    speech+=" La bomba esta encendida."

                else:

                    speech+=" La bomba esta apagada."

        else:

            speech="Sistema listo"

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

        print("Alexa endpoint error:",e)

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

        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        )

    )
