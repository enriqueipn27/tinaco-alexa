# -*- coding: utf-8 -*-

from flask import Flask,jsonify,request
import paho.mqtt.client as mqtt
import json
import time
import threading
import os
import uuid

MQTT_BROKER="broker.hivemq.com"
MQTT_TOPIC="tinaco/enrique/status"

DATA_FILE="last.json"

last_data=None
last_pump=None

app=Flask(__name__)

DEVICE_ID="sistema_tinaco_001"

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

def save_data(data):

    try:

        data_copy=data.copy()

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

def pump_event(state):

    print("Pump change:",state)

def on_message(client,userdata,msg):

    global last_data
    global last_pump

    try:

        data=json.loads(msg.payload.decode())

        # aceptar nuevo formato
        if "lvl" not in data:
            return

        # normalizar datos
        data["level"]=int(data.get("lvl",0))
        data["pump"]="ON" if data.get("p",0)==1 else "OFF"
        data["liters"]=int(data.get("l",0))
        data["height"]=float(data.get("h",0))

        last_data=data

        save_data(data)

        pump=data["pump"]

        if last_pump is None:

            last_pump=pump

        elif pump!=last_pump:

            pump_event(pump)

            last_pump=pump

        print("MQTT:",data)

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

    time.sleep(3)

    try:

        client.reconnect()

    except:

        pass

def start_mqtt():

    def run():

        while True:

            try:

                print("MQTT connecting")

                client=mqtt.Client()

                client.on_connect=on_connect
                client.on_message=on_message
                client.on_disconnect=on_disconnect

                client.connect(MQTT_BROKER,1883,60)

                client.loop_start()

                print("MQTT running")

                while True:

                    time.sleep(60)

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

def get_current_state():

    global last_data

    data=last_data

    if data is None:

        data=load_data()

        if data is None:

            return None

    return data

def build_speech():

    saved=get_current_state()

    if saved is None:

        return "Aún no recibo datos del tinaco"

    level=saved.get("level",0)
    pump=saved.get("pump","OFF")
    wifi=int(saved.get("w",-100))
    height=saved.get("height",0)
    liters=saved.get("liters",0)

    server_time=saved.get("server_time",0)

    level_text=interpret_level(level)

    wifi_text=interpret_wifi(wifi)

    if server_time>0:

        elapsed=int(time.time()-server_time)

    else:

        elapsed=0

    if elapsed<70:

        time_text=f"Última lectura hace {elapsed} segundos."

    elif elapsed<300:

        time_text="Datos con retraso."

    else:

        time_text="No recibo datos recientes."

    speech=f"La bomba está "

    if pump=="ON":

        speech+="encendida."

    else:

        speech+="apagada."

    speech+=f" Nivel {level} por ciento."
    speech+=f" Altura {height} centímetros."
    speech+=f" Volumen {liters} litros."
    speech+=f" Estado {level_text}."
    speech+=f" Señal wifi {wifi_text}."
    speech+=f" {time_text}"

    return speech

@app.route("/tinaco",methods=["POST","GET"])
def tinaco():

    try:

        req=request.get_json(silent=True)

        if req:
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

# SMART HOME

@app.route("/smarthome",methods=["POST"])
def smarthome():

    req=request.get_json()

    print("SmartHome:",json.dumps(req))

    directive=req["directive"]

    name=directive["header"]["name"]

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

                        "displayCategories":[

                            "SWITCH"

                        ],

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

                                    "supported":[

                                        {

                                            "name":"powerState"

                                        }

                                    ],

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

    data=get_current_state()

    if data is None:

        power="OFF"

    else:

        power=data.get("pump","OFF")

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

if __name__=="__main__":

    app.run(

        host="0.0.0.0",

        port=int(os.environ.get("PORT",5000))

    )
