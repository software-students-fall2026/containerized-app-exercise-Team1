from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/play/manual")
def play_manual():
    return render_template("game.html")

@app.route("/play/gesture")
def play_gesture():
    return "gesture game mode in progess"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)