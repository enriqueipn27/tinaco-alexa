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

        data_copy=data.copy()

        # tiempo del servidor (clave del sistema)
        data_copy["server_time"]=time.time()

        with open(DATA_FILE,"w") as f:

            json.dump(data_copy,f)

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

    try:

        data=json.loads(msg.payload.decode())

        if "level" not in data:
            return

        last_data=data

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

        "last_data":data

    })


def build_speech():

    global last_data

    saved=last_data

    if saved is None:

        saved=load_data()

        if saved is None:

            return "Aún no recibo datos del tinaco"

    level=saved.get("level",0)

    pump=saved.get("pump","OFF")

    wifi=saved.get("w",-100)

    server_time=saved.get("server_time",0)

    level_text=interpret_level(level)

    wifi_text=interpret_wifi(wifi)


    # tiempo real correcto
    if server_time>0:

        elapsed=int(time.time()-server_time)

    else:

        elapsed=0


    # interpretación inteligente
    if elapsed<70:

        time_text=f"Última lectura hace {elapsed} segundos."

    elif elapsed<300:

        time_text="Datos con retraso."

    else:

        time_text="No recibo datos recientes del sensor."


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
