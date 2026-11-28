"""Serve fingertip tracking requests."""
from functools import lru_cache
from time import perf_counter
from flask import Flask, jsonify, request
from pymongo.errors import PyMongoError
from storage import save_tracking_result
from tracker import HandTracker, InvalidFrame, decode_frame


@lru_cache(maxsize=1)
def get_tracker():
    """Reuse one hand tracker across requests."""
    return HandTracker()


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024


def detect(pixels):
    """Detect a fingertip and measure inference time."""
    tracker = get_tracker()
    start = perf_counter()
    result = tracker.detect(pixels)
    result["inference_ms"] = round((perf_counter() - start) * 1000, 2)
    return result


def save_sample(result):
    """Save every tenth tracking result when MongoDB is available."""
    if result["frame_id"] % 10:
        return False
    try:
        save_tracking_result(result)
    except PyMongoError:
        app.logger.warning("Could not save tracking result")
        return False
    return True


@app.route("/")
def home():
    """Return the ML service landing response."""
    return "in progress"


@app.route("/track", methods=["POST"])
def track():
    """Process an uploaded frame and return its tracking result."""
    frame = request.files.get("frame")
    frame_id = request.form.get("frame_id", type=int)
    if frame is None or frame_id is None:
        return jsonify(error="Send a frame and integer frame_id"), 400
    try:
        pixels = decode_frame(frame.read())
    except InvalidFrame as error:
        return jsonify(error=str(error)), 400
    result = detect(pixels)
    result["session_id"] = request.form.get("session_id", "")
    result["frame_id"] = frame_id
    return jsonify(**result, saved=save_sample(result))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
