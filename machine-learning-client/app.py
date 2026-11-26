#using this as a dummy server for now
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "ML Client in running"

@app.route("/track", methods=["POST"])
def track():
    return jsonify({"found": True, "x": 150, "y": 200})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)