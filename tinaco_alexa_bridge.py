242
243
244
245
246
247
248
249
250
251
252
253
254
255
256
257
258
259
260
261
262
263
264
265
266
267
268
269
270
271
272
273
274
275
276
277
278
279
280
281
282
283
284
285
286
287
288
289
290
291
292
293
294
295
296
297
298
299
300
301
302
303
304
305
306
307
308
309
310
311
312
313
314
315
316
317
318
319
320
321
322
323
324
import uuid

        data = compute_alerts('enrique', devices['enrique'])

        if req_type == 'LaunchRequest':
            return alexa_speak('Bienvenido a mi tinaco. Puedes preguntarme nivel, estado o alertas del agua.')

        if req_type == 'IntentRequest':
            intent = req['request']['intent']['name']

            if intent == 'NivelIntent':
                texto = f"{data['speech']} El nivel actual es de {data['level']} por ciento, con aproximadamente {data['liters']} litros disponibles."
                return alexa_speak(texto)

            if intent == 'EstadoIntent':
                texto = f"{data['speech']} La altura del agua es de {data['height']} centímetros y la señal wifi es {data['rssi']} decibeles."
                return alexa_speak(texto)

            if intent == 'AlertaIntent':
                return alexa_speak(data['speech'])

            if intent in ['AMAZON.StopIntent','AMAZON.CancelIntent','AMAZON.NavigateHomeIntent']:
                return alexa_speak('Hasta luego.', True)

        return alexa_speak('No entendí tu solicitud. Puedes preguntarme nivel, estado o alertas.')

    except Exception as e:
        print('ALEXA ERROR:', e)
        return alexa_speak('Ocurrió una falla temporal en mi tinaco.')

#################################################
# OAUTH
#################################################
@app.route('/auth')
def auth():
    redirect_uri = request.args.get("redirect_uri")
    state = request.args.get("state")
    client_id = request.args.get("client_id")
    scope = request.args.get("scope")
    if client_id != VALID_CLIENT_ID or scope != VALID_SCOPE:
        return "unauthorized", 401
    auth_code = str(uuid.uuid4())
    auth_codes[auth_code] = {"client_id": client_id,"created": time.time(),"user": "enrique"}
    return redirect(f"{redirect_uri}?state={state}&code={auth_code}")

@app.route('/token', methods=['POST'])
def token():
    grant_type = request.form.get("grant_type")
    code = request.form.get("code")
    refresh = request.form.get("refresh_token")
    client_id = request.form.get("client_id")
    client_secret = request.form.get("client_secret")
    if client_id != VALID_CLIENT_ID or client_secret != VALID_CLIENT_SECRET:
        return jsonify({"error": "invalid_client"}), 401

    if grant_type == "authorization_code":
        if code not in auth_codes:
            return jsonify({"error": "invalid_grant"}), 400
        access_token = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        access_tokens[access_token] = {"user": "enrique", "created": time.time()}
        refresh_tokens[refresh_token] = {"user": "enrique", "created": time.time()}
        return jsonify({"access_token": access_token,"token_type": "Bearer","expires_in": 86400,"refresh_token": refresh_token})

    elif grant_type == "refresh_token":
        if refresh not in refresh_tokens:
            return jsonify({"error": "invalid_refresh"}), 400
        new_access = str(uuid.uuid4())
        access_tokens[new_access] = {"user": "enrique", "created": time.time()}
        return jsonify({"access_token": new_access,"token_type": "Bearer","expires_in": 86400,"refresh_token": refresh})

    return jsonify({"error": "unsupported_grant_type"}), 400

@app.route('/validate')
def validate():
    token = request.args.get("token")
    if token in access_tokens:
        return jsonify({"valid": True, "user": access_tokens[token]["user"]})
    return jsonify({"valid": False}), 401

@app.route('/')
def home():
    return 'Mi Tinaco Render FailSoft V3 Alexa activo'

Use Control + Shift + m to toggle the tab key moving focus. Alternatively, use esc then tab to move to the nex
