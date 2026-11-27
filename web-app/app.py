from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)
ML_CLIENT_URL = "http://ml-client:5000/track"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/play/<mode>")
def play(mode):
    if mode not in ["manual", "gesture"]:
        return "invalid", 404
    return render_template("game.html", mode=mode)

@app.route("/api/track", methods=["POST"])
def track():
    try:
        response = requests.post(
            ML_CLIENT_URL,
            files=request.files,
            data=request.form,
            timeout=3
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": "could not reach ml client", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)