from flask import Flask, request, jsonify

app = Flask(__name__)

# 🔐 TOKEN
@app.route("/token", methods=["POST"])
def token():
    return jsonify({
        "access_token": "dummy-token",
        "token_type": "Bearer",
        "expires_in": 3600
    })

# 🔐 AUTH
@app.route("/auth")
def auth():
    redirect_uri = request.args.get("redirect_uri")
    state = request.args.get("state")

    print("AUTH REQUEST:", redirect_uri, state)

    return f'''
    <html>
    <body>
    <h2>Vinculando cuenta...</h2>
    <script>
    window.location.href = "{redirect_uri}?state={state}&code=1234";
    </script>
    </body>
    </html>
    '''

# (opcional pero recomendado)
@app.route("/debug")
def debug():
    return jsonify({
        "level": 97,
        "pump": "OFF"
    })
