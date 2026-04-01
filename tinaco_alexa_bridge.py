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

        print("MQTT recibido:",data)

    except Exception as e:

        print("JSON error:",e)


def on_connect(client,userdata,flags,rc):

    print("MQTT conectado codigo:",rc)

    if rc==0:

        client.subscribe(MQTT_TOPIC)

        print("Suscrito a:",MQTT_TOPIC)

    else:

        print("Error MQTT codigo:",rc)


def mqtt_loop():

    while True:

        try:

            print("Intentando conectar MQTT...")

            client=mqtt.Client(protocol=mqtt.MQTTv311)

            client.on_connect=on_connect
            client.on_message=on_message

            client.reconnect_delay_set(
                min_delay=1,
                max_delay=30
            )

            client.connect(
                MQTT_BROKER,
                1883,
                60
            )

            client.loop_forever()

        except Exception as e:

            print("MQTT reconectando:",e)

            time.sleep(5)


def start_mqtt():

    thread=threading.Thread(target=mqtt_loop)

    thread.daemon=True

    thread.start()

    print("MQTT thread iniciado")


# iniciar MQTT
start_mqtt()


@app.route("/")
def home():

    return "Tinaco Alexa bridge running"


# Endpoint debug
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

        # Permitir ver datos en navegador
        if request.method=="GET":

            return jsonify({

                "status":"running",

                "last_data":last_data,

                "last_update":last_update

            })

        req=request.json

        if not req:

            speech="Sistema funcionando correctamente"

        else:

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

            # IntentRequest
            elif req_type=="IntentRequest":

                if last_data is None:

                    speech="Aun no recibo datos del tinaco"

                else:

                    level=last_data.get("level",0)

                    pump=last_data.get("pump","OFF")

                    age=int(
                        time.time()-last_update
                    )

                    level_text=interpret_level(level)

                    speech=f"El nivel del tinaco es {level} por ciento."

                    speech+=f" Estado {level_text}."

                    if pump=="ON":

                        speech+=" La bomba esta encendida."

                    else:

                        speech+=" La bomba esta apagada."

                    if age>90:

                        speech+=f" Ultima actualizacion hace {age} segundos."

            else:

                speech="No entendi la solicitud"

        response={

            "version":"1.0",

            "response":{

                "outputSpeech":{

                    "type":"PlainText",

                    "text":speech

                },

                "shouldEndSession":True

            }

        }

        return jsonify(response)

    except Exception as e:

        print("Endpoint error:",e)

        return jsonify({

            "version":"1.0",

            "response":{

                "outputSpeech":{

                    "type":"PlainText",

                    "text":"Error leyendo datos del tinaco"

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
