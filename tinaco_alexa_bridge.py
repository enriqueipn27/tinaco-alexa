# -*- coding: utf-8 -*-

import paho.mqtt.client as mqtt
from flask import Flask,jsonify,request
import json
import time
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

        last_data=data

        last_update=time.time()

        print("MQTT:",data)

    except Exception as e:

        print("JSON error",e)

def on_connect(client,userdata,flags,rc):

    print("MQTT conectado")

    client.subscribe(MQTT_TOPIC)

client=mqtt.Client()

client.on_connect=on_connect

client.on_message=on_message

client.connect(MQTT_BROKER,1883,60)

client.loop_start()

@app.route("/")

def home():

    return "Tinaco Alexa Bridge Running"

@app.route("/tinaco",methods=["POST","GET"])

def tinaco():

    global last_data
    global last_update

    try:

        if last_data is None:

            speech="No hay datos del tinaco todavia"

        else:

            level=last_data["level"]

            pump=last_data["pump"]

            age=int(time.time()-last_update)

            level_text=interpret_level(level)

            speech=f"El nivel del tinaco es {level} por ciento."

            speech+=f" Estado {level_text}."

            if pump=="ON":

                speech+=" La bomba esta encendida."

            else:

                speech+=" La bomba esta apagada."

            if age>60:

                speech+=f" Ultima actualizacion hace {age} segundos."

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

    port=int(os.environ.get("PORT",5000))

    app.run(host="0.0.0.0",port=port)