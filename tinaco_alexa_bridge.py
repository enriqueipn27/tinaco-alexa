@app.route("/tinaco",methods=["POST","GET"])
def tinaco():

    global last_data
    global last_update

    try:

        if last_data is None or "level" not in last_data:

            speech="Esperando datos del tinaco"

        else:

            level=last_data.get("level",0)

            pump=last_data.get("pump","OFF")

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