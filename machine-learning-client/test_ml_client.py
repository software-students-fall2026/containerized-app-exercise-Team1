"""Test the ML routes, tracker, storage, and camera preview."""
import io
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image
from pymongo.errors import ServerSelectionTimeoutError

import app
import check_mediapipe as camera
import download_model
import storage
import tracker


def image_bytes(size=(16, 12)):
    """Generate a blank PNG for an upload."""
    stream = io.BytesIO()
    Image.new("RGB", size).save(stream, format="PNG")
    stream.seek(0)
    return stream


@pytest.fixture(name="client")
def ml_client():
    """Create a Flask test client."""
    return app.app.test_client()


def test_real_blank_frame(client, monkeypatch):
    """Check blank-frame detection and sampling at frames zero and ten."""
    saved = []
    monkeypatch.setattr(
        app, "save_tracking_result", lambda row: saved.append(row.copy())
    )
    assert client.get("/").status_code == 200
    for frame_id in (0, 1, 10):
        response = client.post(
            "/track",
            data={
                "frame": (image_bytes(), "frame.png"),
                "frame_id": str(frame_id),
                "session_id": "round-1",
            },
        )
        assert response.status_code == 200
        row = response.get_json()
        assert (row["found"], row["x"], row["y"]) == (False, None, None)
        assert row["frame_id"] == frame_id and row["session_id"] == "round-1"
        assert row["inference_ms"] >= 0
        assert row["saved"] == (frame_id in (0, 10))
    assert [row["frame_id"] for row in saved] == [0, 10]


def test_hand_found_through_route(client, monkeypatch):
    """Return normalized fingertip coordinates through the tracking route."""
    tip = SimpleNamespace(x=0.3123456, y=0.75)
    landmarks = SimpleNamespace(hand_landmarks=[[None] * 8 + [tip]])
    detector = MagicMock()
    detector.detect.side_effect = lambda pixels: tracker.fingertip_result(landmarks)
    monkeypatch.setattr(app, "get_tracker", lambda: detector)
    result = client.post(
        "/track", data={"frame": (image_bytes(), "frame.png"), "frame_id": "1"}
    ).get_json()
    assert (result["found"], result["x"], result["y"]) == (True, 0.31235, 0.75)
    assert result["saved"] is False


@pytest.mark.parametrize("value", [None, "abc"])
def test_bad_frame_id(client, value):
    """Reject missing and noninteger frame IDs."""
    fields = {"frame": (image_bytes(), "frame.png")}
    if value is not None:
        fields["frame_id"] = value
    assert client.post("/track", data=fields).status_code == 400


def test_missing_and_invalid_image(client):
    """Reject absent uploads and undecodable images."""
    assert client.post("/track", data={"frame_id": "2"}).status_code == 400
    response = client.post(
        "/track", data={"frame_id": "2", "frame": (io.BytesIO(b"bad"), "bad.jpg")}
    )
    assert response.status_code == 400
    assert "decode" in response.get_json()["error"]


def test_decode_size_and_direction():
    """Check resizing, mirroring, and the image size limit."""
    image = Image.new("RGB", (800, 400), "red")
    image.paste("blue", (400, 0, 800, 400))
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    pixels = tracker.decode_frame(stream.getvalue())
    assert pixels.shape == (320, 640, 3)
    assert pixels[0, 0].tolist() == [0, 0, 255]
    with pytest.raises(tracker.InvalidFrame):
        tracker.decode_frame(image_bytes((1921, 1080)).read())


def test_database_unavailable_preserves_tracking(client, monkeypatch):
    """Keep returning detections when a database write fails."""

    def unavailable(result):
        raise ServerSelectionTimeoutError("offline")

    monkeypatch.setattr(app, "save_tracking_result", unavailable)
    response = client.post(
        "/track", data={"frame_id": "10", "frame": (image_bytes(), "frame.png")}
    )
    assert response.status_code == 200
    assert response.get_json()["saved"] is False
    assert response.get_json()["found"] is False


def test_storage_document(monkeypatch):
    """Insert a timestamped record in the configured database."""
    connection = MagicMock()
    monkeypatch.setattr(storage, "MongoClient", connection)
    monkeypatch.setenv("MONGO_URI", "mongodb://mongodb:27017")
    monkeypatch.setenv("MONGO_DB", "fruit_ninja")
    storage.get_client.cache_clear()
    try:
        row = {
            "frame_id": 10,
            "session_id": "round-1",
            "found": True,
            "x": 0.3,
            "y": 0.4,
        }
        storage.save_tracking_result(row)
        connection.assert_called_once_with("mongodb://mongodb:27017", timeoutMS=500)
        collection = connection.return_value["fruit_ninja"]["tracking_results"]
        document = collection.insert_one.call_args.args[0]
        assert document["created_at"].utcoffset().total_seconds() == 0
        assert {k: document[k] for k in row} == row
    finally:
        storage.get_client.cache_clear()


def test_download_model(tmp_path, monkeypatch):
    """Write downloaded model bytes to the expected path."""
    monkeypatch.setattr(download_model, "__file__", str(tmp_path / "download_model.py"))
    monkeypatch.setattr(
        download_model, "urlopen", lambda url, timeout: io.BytesIO(b"model")
    )
    download_model.download()
    assert (tmp_path / "models/hand_landmarker.task").read_bytes() == b"model"


def test_camera_preview(monkeypatch):
    """Draw a preview and release resources when the user quits."""
    device = MagicMock()
    device.read.return_value = (True, np.zeros((48, 64, 3), dtype=np.uint8))
    model = MagicMock()
    model.detect.side_effect = [
        {"found": False, "x": None, "y": None},
        {"found": True, "x": 0.5, "y": 0.25},
    ]
    monkeypatch.setattr(sys, "argv", ["check_mediapipe.py"])
    monkeypatch.setattr(camera, "HandTracker", lambda: model)
    monkeypatch.setattr(camera.cv2, "VideoCapture", lambda index: device)
    preview = MagicMock()
    monkeypatch.setattr(camera.cv2, "imshow", preview)
    monkeypatch.setattr(camera.cv2, "waitKey", lambda delay: ord("q"))
    monkeypatch.setattr(camera.cv2, "destroyAllWindows", lambda: None)
    camera.main()
    preview.assert_called_once()
    model.close.assert_called_once()
    device.release.assert_called_once()


def camera_fixture(monkeypatch, argv, detections, device=None):
    """Configure a mock detector and camera for preview tests."""
    model = MagicMock()
    model.detect.side_effect = detections
    monkeypatch.setattr(sys, "argv", ["check_mediapipe.py", *argv])
    monkeypatch.setattr(camera, "HandTracker", lambda: model)
    monkeypatch.setattr(camera.cv2, "VideoCapture", lambda index: device)
    monkeypatch.setattr(camera.cv2, "destroyAllWindows", lambda: None)
    return model


def test_prepare_frame_encode_failure(monkeypatch):
    """Raise an error when JPEG encoding fails."""
    monkeypatch.setattr(camera.cv2, "imencode", lambda ext, frame: (False, None))
    with pytest.raises(RuntimeError, match="encode"):
        camera.prepare_frame(np.zeros((48, 64, 3), dtype=np.uint8))


def test_camera_no_camera_flag(monkeypatch):
    """Check a blank frame without opening a camera."""
    model = camera_fixture(
        monkeypatch, ["--no-camera"], [{"found": False, "x": None, "y": None}]
    )
    camera.main()
    model.close.assert_called_once()


def test_camera_blank_image_with_hand_fails(monkeypatch):
    """Reject a hand detection on the blank test image."""
    model = camera_fixture(
        monkeypatch, ["--no-camera"], [{"found": True, "x": 0.5, "y": 0.5}]
    )
    with pytest.raises(RuntimeError, match="no hand"):
        camera.main()
    model.close.assert_called_once()


def test_camera_cannot_open(monkeypatch):
    """Release resources when the camera cannot open."""
    device = MagicMock()
    device.isOpened.return_value = False
    model = camera_fixture(
        monkeypatch, [], [{"found": False, "x": None, "y": None}], device
    )
    with pytest.raises(RuntimeError, match="Cannot open camera"):
        camera.main()
    device.release.assert_called_once()
    model.close.assert_called_once()


def test_camera_no_frame(monkeypatch):
    """Release resources when the camera returns no frame."""
    device = MagicMock()
    device.read.return_value = (False, None)
    model = camera_fixture(
        monkeypatch, [], [{"found": False, "x": None, "y": None}], device
    )
    with pytest.raises(RuntimeError, match="no frame"):
        camera.main()
    device.release.assert_called_once()
    model.close.assert_called_once()


def test_real_tracker_video_timestamps_and_close():
    """Exercise the real tracker with increasing video timestamps."""
    hand_tracker = tracker.HandTracker()
    blank = np.zeros((48, 64, 3), dtype=np.uint8)
    try:
        for _ in range(3):
            assert hand_tracker.detect(blank) == {"found": False, "x": None, "y": None}
        first = hand_tracker.last_timestamp
        hand_tracker.detect(blank)
        assert hand_tracker.last_timestamp > first
    finally:
        hand_tracker.close()
