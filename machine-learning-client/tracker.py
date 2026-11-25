import io
from pathlib import Path
from threading import Lock
import mediapipe as mp
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError


class InvalidFrame(ValueError):
    pass


def decode_frame(data):
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > 1920 * 1080:
                raise InvalidFrame("Frame must contain at most 1920 * 1080 pixels")
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((640, 480))
            return np.array(ImageOps.mirror(image))
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise InvalidFrame("Cannot decode this image") from error


def fingertip_result(result):
    if not result.hand_landmarks:
        return {"found": False, "x": None, "y":None}
    tip = result.hand_landmarks[0][8]
    return {
        "found": True,
        "x": round(max(0, min(1, float(tip.x))), 5),
        "y": round(max(0, min(1, float(tip.y))), 5)
    }

class HandTracker:
    def __init__(self, model_path=None):
        model_path = (
            model_path
            or Path(__file__).parent / "models/hand_landmarker.task"
        )
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(
                model_asset_path=str(model_path)
            ),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
        )
        self.model = mp.tasks.vision.HandLandmarker.create_from_options(options)
        self.lock = Lock()

    def detect(self, pixels):
        image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=pixels,
        )

        with self.lock:
            result = self.model.detect(image)

        return fingertip_result(result)

    def close(self):
        self.model.close()