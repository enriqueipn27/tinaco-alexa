@app.route("/tinaco",methods=["POST","GET"])
def tinaco():

    global last_data
    global last_update

    try:

        req=request.get_json(force=True)

        print("Alexa:",req)

        req_type=req.get("request",{}).get("type","")

        def wifi_text(rssi):

            try:

                rssi=int(rssi)

                if rssi>=-60:
                    return "Señal wifi excelente."

                if rssi>=-70:
                    return "Señal wifi buena."

                if rssi>=-80:
                    return "Señal wifi regular."

                return "Señal wifi débil."

            except:

                return ""


        def build_speech():

            if last_data is None:

                return "Aun no recibo datos del tinaco"

            level=last_data.get("level",0)

            pump=last_data.get("pump","OFF")

            wifi=last_data.get("w",-100)

            level_text=interpret_level(level)

            age=int(time.time()-last_update)

            speech=f"Nivel {level} por ciento."

            speech+=f" Estado {level_text}."

            if pump=="ON":

                speech+=" Bomba encendida."

            else:

                speech+=" Bomba apagada."

            speech+=f" Última lectura hace {age} segundos."

            speech+=wifi_text(wifi)

            return speech


        # LaunchRequest → RESPUESTA INMEDIATA
        if req_type=="LaunchRequest":

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


        # IntentRequest
        if req_type=="IntentRequest":

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


        return jsonify({

            "version":"1.0",

            "response":{

                "outputSpeech":{

                    "type":"PlainText",

                    "text":"No entendi la solicitud"

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
