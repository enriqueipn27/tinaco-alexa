# -*- coding: utf-8 -*-

from flask import Flask,request,jsonify
import paho.mqtt.client as mqtt
import json
import time
import threading
import os
import uuid

####################################
# CONFIG
####################################

MQTT_BROKER="broker.hivemq.com"
MQTT_TOPIC="tinaco/enrique/status"

DATA_FILE="last.json"

DEVICE_ID="sistema_tinaco_001"

####################################
# GLOBAL STATE
####################################

last_data=None

data_lock=threading.Lock()

mqtt_started=False

app=Flask(__name__)

####################################
# INTERPRETACION
####################################

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
        return "excelente"

    if w>=-70:
        return "buena"

    if w>=-80:
        return "regular"

    return "débil"

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

    norm={}

    norm["level"]=int(data.get("lvl",0))

    norm["pump"]="ON" if data.get("p",0)==1 else "OFF"

    norm["liters"]=int(data.get("l",0))

    norm["height"]=float(data.get("h",0))

    norm["wifi"]=int(data.get("w",-100))

    norm["mcu_time"]=data.get("t",0)

    norm["server_time"]=time.time()

    return norm

####################################
# MQTT
####################################

def on_message(client,userdata,msg):

    global last_data

    try:

        raw=json.loads(msg.payload.decode())

        if "lvl" not in raw:
            return

        norm=normalize(raw)

        with data_lock:

            last_data=norm

            save_data(norm)

        print("MQTT:",norm)

    except Exception as e:

        print("JSON error:",e)

def on_connect(client,userdata,flags,rc):

    if rc==0:

        print("MQTT conectado")

        client.subscribe(MQTT_TOPIC)

    else:

        print("MQTT error",rc)

def on_disconnect(client,userdata,rc):

    print("MQTT desconectado")

def mqtt_loop():

    while True:

        try:

            print("MQTT connecting")

            client=mqtt.Client()

            client.on_connect=on_connect

            client.on_message=on_message

            client.on_disconnect=on_disconnect

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

    thread=threading.Thread(target=mqtt_loop)

    thread.daemon=True

    thread.start()

start_mqtt()

####################################
# STATE
####################################

def get_state():

    global last_data

    with data_lock:

        if last_data:
            return last_data

    return load_data()

####################################
# SPEECH
####################################

def build_speech():

    data=get_state()

    if data is None:

        return "Sistema tinaco activo pero aún sin datos recientes."

    level=data.get("level",0)

    pump=data.get("pump","OFF")

    wifi=data.get("wifi",-100)

    height=data.get("height",0)

    liters=data.get("liters",0)

    elapsed=int(time.time()-data.get("server_time",time.time()))

    level_text=interpret_level(level)

    wifi_text=interpret_wifi(wifi)

    if elapsed<60:

        time_text=f"Última lectura hace {elapsed} segundos."

    elif elapsed<300:

        time_text=f"Último dato hace {elapsed} segundos."

    elif elapsed<1800:

        mins=int(elapsed/60)

        time_text=f"Último dato hace {mins} minutos."

    else:

        time_text="Último dato no reciente."

    speech="Estado del tinaco."

    if pump=="ON":

        speech+=" Bomba encendida."

    else:

        speech+=" Bomba apagada."

    speech+=f" Nivel {level} por ciento."

    speech+=f" Volumen {liters} litros."

    speech+=f" Altura {round(height,1)} centímetros."

    speech+=f" Estado {level_text}."

    speech+=f" Señal wifi {wifi_text}."

    speech+=f" {time_text}"

    return speech

####################################
# ALEXA RESPONSE
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

@app.route("/health")
def health():

    data=get_state()

    if data:

        return {"status":"ok"}

    return {"status":"waiting_data"}

@app.route("/tinaco",methods=["POST"])
def tinaco():

    try:

        req=request.get_json(silent=True)

        speech=build_speech()

        return alexa_response(speech)

    except Exception as e:

        print(e)

        return alexa_response("Error sistema tinaco")

####################################
# SMART HOME
####################################

@app.route("/smarthome",methods=["POST"])
def smarthome():

    req=request.get_json()

    name=req["directive"]["header"]["name"]

    if name=="Discover":

        return discovery_response()

    if name=="ReportState":

        return report_state()

    return {}

def discovery_response():

    return {

        "event":{

            "header":{

                "namespace":"Alexa.Discovery",

                "name":"Discover.Response",

                "payloadVersion":"3",

                "messageId":str(uuid.uuid4())

            },

            "payload":{

                "endpoints":[

                    {

                        "endpointId":DEVICE_ID,

                        "manufacturerName":"Enrique IoT",

                        "friendlyName":"Sistema tinaco",

                        "displayCategories":["SWITCH"],

                        "capabilities":[

                            {

                                "type":"AlexaInterface",

                                "interface":"Alexa",

                                "version":"3"

                            },

                            {

                                "type":"AlexaInterface",

                                "interface":"Alexa.PowerController",

                                "version":"3",

                                "properties":{

                                    "supported":[{"name":"powerState"}],

                                    "retrievable":True

                                }

                            }

                        ]

                    }

                ]

            }

        }

    }

def report_state():

    data=get_state()

    if data:

        power=data["pump"]

    else:

        power="OFF"

    return {

        "context":{

            "properties":[

                {

                    "namespace":"Alexa.PowerController",

                    "name":"powerState",

                    "value":power,

                    "timeOfSample":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),

                    "uncertaintyInMilliseconds":500

                }

            ]

        },

        "event":{

            "header":{

                "namespace":"Alexa",

                "name":"StateReport",

                "payloadVersion":"3",

                "messageId":str(uuid.uuid4())

            },

            "endpoint":{

                "endpointId":DEVICE_ID

            },

            "payload":{}

        }

    }

####################################
# MAIN
####################################

if __name__=="__main__":

    app.run(

        host="0.0.0.0",

        port=int(os.environ.get("PORT",5000))

    )
