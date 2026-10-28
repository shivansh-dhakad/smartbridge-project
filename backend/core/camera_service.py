
import cv2
import time
from datetime import datetime, timezone

from core.face_detection import FaceDetector
from core.face_tracker import FaceTracker


class CameraService:
    def __init__(self, camera_id=0, source=None):
        # Use webcam by default, or pass a video file path.
        self.source = source if source is not None else camera_id
        self.cap = None
        self.is_running = False

        self.detector = FaceDetector()
        self.tracker = FaceTracker()

        self.start_time = time.time()
        self.tracking_records = []

    def start(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(self.source)

            if not self.cap.isOpened():
                self.cap.release()
                self.cap = None
                raise RuntimeError(
                    f"Unable to open video source: {self.source}"
                )

        self.is_running = True

    def stop(self):
        self.is_running = False

        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def get_frame(self):
        if not self.is_running or self.cap is None:
            return None

        success, frame = self.cap.read()

        if not success:
            return None

        return frame

    def process_frame(self, frame):
        detections = self.detector.process_frame(frame)
        tracks = self.tracker.update(detections)

        timestamp = datetime.now(timezone.utc).isoformat()
        elapsed_seconds = round(time.time() - self.start_time, 2)

        for track in tracks:
            x, y, w, h = track["bbox"]
            participant_id = track["participant_id"]

            # Draw the bounding box and participant ID.
            cv2.rectangle(
                frame, (x, y), (x + w, y + h),
                (0, 255, 0), 2
            )

            cv2.putText(
                frame,
                f"Participant {participant_id}",
                (x, max(y - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

            # Store structured tracking information.
            self.tracking_records.append({
                "participant_id": participant_id,
                "timestamp": timestamp,
                "elapsed_seconds": elapsed_seconds,
                "bbox": {
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h
                }
            })

        return frame, tracks

    def get_tracking_records(self):
        return list(self.tracking_records)
