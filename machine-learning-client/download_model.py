from pathlib import Path
from urllib.request import urlopen

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

def download():
    target = Path(__file__).parent / "models/hand_landmarker.task"
    target.parent.mkdir(exist_ok=True)
    temp= target.with_suffix(".tmp")
    with urlopen(MODEL_URL, timeout=60) as response:
        temp.write_bytes(response.read())
    temp.replace(target)
    print("Downloaded to {target}")

if __name__ == "__main__":
    download()