import argparse
import cv2
import numpy as np
from tracker import HandTracker, decode_frame

def prepare_frame(frame):
    height, width = frame.shape[:2]
    scale = min(640 / width, 480 / height, 1)
    frame = cv2.resize(frame, (int(width * scale), int(height * scale)))
    success, encoded = cv2.imencode(".jpg", frame)
    if not success:
        raise RuntimeError("Could not encode the camera frame")
    return decode_frame(encoded.tobytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-camera", action="store_true")
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()

    print("Loading the MediaPipe model...")
    tracker = HandTracker()
    camera = None

    try:
        print("PASS: model loaded")
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        result = tracker.detect(prepare_frame(blank))
        print("Blank-image result:", result)
        if result != {"found": False, "x": None, "y": None}:
            raise RuntimeError("FAIL: the blank image should contain no hand")
        print("PASS: blank image correctly returned no hand")

        if args.no_camera:
            return

        camera = cv2.VideoCapture(args.camera)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not camera.isOpened():
            raise RuntimeError("Cannot open camera. Check camera permissions.")

        print("Show one hand. Click the video window and press Q to quit.")
        while True:
            success, frame = camera.read()
            if not success:
                raise RuntimeError("Camera opened but no frame was received")

            pixels = prepare_frame(frame)
            result = tracker.detect(pixels)
            preview = cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR)
            height, width = preview.shape[:2]
            label = "found: false | No hand"

            if result["found"]:
                x, y = result["x"], result["y"]
                point = (round(x * (width - 1)), round(y * (height - 1)))
                cv2.circle(preview, point, 10, (0, 255, 0), -1)
                label = f"found: true | x: {x:.3f}, y: {y:.3f}"

            cv2.putText(preview, label, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imshow("MediaPipe test - press Q to quit", preview)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        if camera is not None:
            camera.release()
        cv2.destroyAllWindows()
        tracker.close()
        print("Test finished; model and camera released.")


if __name__ == "__main__":
    main()
