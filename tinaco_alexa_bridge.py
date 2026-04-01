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


def alexa_response(text):

    return {
        "version":"1.0",
        "response":{
            "outputSpeech":{
                "type":"PlainText",
                "text":text
            },
            "reprompt":{
                "outputSpeech":{
                    "type":"PlainText",
                    "text":"Puedes preguntarme el nivel del tinaco"
                }
            },
            "shouldEndSession":True
        }
    }


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

    print("MQTT conectado:",rc)

    if rc==0:

        client.subscribe(MQTT_TOPIC)

        print("Suscrito:",MQTT_TOPIC)


def mqtt_loop():

    while True:

        try:

            print("Conectando MQTT")

            client=mqtt.Client()

            client.on_connect=on_connect
            client.on_message=on_message

            client.connect(
                MQTT_BROKER,
                1883,
                60
            )

            client.loop_forever()

        except Exception as e:

            print("MQTT error:",e)

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

        if request.method=="GET":

            return jsonify({

                "status":"running",

                "last_data":last_data

            })

        req=request.get_json(silent=True)

        print("Alexa:",req)

        req_type=req.get(
            "request",
            {}
        ).get(
            "type",
            ""
        )

        if req_type=="LaunchRequest":

            return jsonify(
                alexa_response(
                    "Puedes preguntarme el nivel del tinaco"
                )
            )


        if req_type=="IntentRequest":

            if last_data is None:

                return jsonify(
                    alexa_response(
                        "Aun no recibo datos del tinaco"
                    )
                )

            level=last_data.get("level",0)

            pump=last_data.get("pump","OFF")

            level_text=interpret_level(level)

            speech=f"El nivel del tinaco es {level} por ciento."

            speech+=f" Estado {level_text}."

            if pump=="ON":

                speech+=" La bomba esta encendida."

            else:

                speech+=" La bomba esta apagada."

            return jsonify(
                alexa_response(speech)
            )


        return jsonify(
            alexa_response("Sistema listo")
        )

    except Exception as e:

        print("Alexa error:",e)

        return jsonify(
            alexa_response(
                "Error interno del sistema"
            )
        )


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
