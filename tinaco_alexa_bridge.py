from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/auth")
def auth():
    redirect_uri = request.args.get("redirect_uri")
    state = request.args.get("state")

    print("AUTH REQUEST:", redirect_uri, state)

    return f'''
    <html>
    <script>
    window.location.href = "{redirect_uri}?state={state}&code=1234";
    </script>
    </html>
    '''

@app.route("/token", methods=["POST"])
def token():
    return jsonify({
        "access_token": "dummy-token",
        "token_type": "Bearer",
        "expires_in": 3600
    })

@app.route("/debug")
def debug():
    return jsonify({
        "level": 97,
        "pump": "OFF"
    })
