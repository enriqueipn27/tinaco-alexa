# SOLO build_speech cambia

def build_speech():

    global last_data

    if last_data is None:

        last_data=load_data()

        if last_data is None:

            return "Aún no recibo datos del tinaco"

    level=last_data.get("level",0)
    pump=last_data.get("pump","OFF")
    wifi=last_data.get("w",-100)

    level_text=interpret_level(level)
    wifi_text=interpret_wifi(wifi)

    server_time=last_data.get("server_time",0)

    if server_time>0:

        elapsed=int(time.time()-server_time)

    else:

        elapsed=0


    # SOLO ESTO (igual que tu dashboard)

    if elapsed<60:

        time_text=f"Última lectura hace {elapsed} segundos."

    elif elapsed<120:

        time_text="Datos recientes."

    else:

        time_text="Datos atrasados."


    speech=f"Nivel {level} por ciento."

    speech+=f" Estado {level_text}."

    speech+=f" {time_text}"

    speech+=f" {wifi_text}."

    if pump=="ON":

        speech+=" Bomba encendida."

    else:

        speech+=" Bomba apagada."

    return speech
