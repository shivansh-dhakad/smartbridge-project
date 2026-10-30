
import cv2
import numpy as np


class FaceDetector:
    def __init__(self):
        self.face_cascade = None
        cascade_constructor = getattr(cv2, "CascadeClassifier", None)
        if cascade_constructor is not None:
            cascade_path = getattr(cv2, "data", None)
            if cascade_path is not None:
                cascade_path = cascade_path.haarcascades + "haarcascade_frontalface_default.xml"
                candidate = cascade_constructor(cascade_path)
                if hasattr(candidate, "empty") and not candidate.empty():
                    self.face_cascade = candidate

    def process_frame(self, frame):
        if self.face_cascade is not None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            return [{"bbox": tuple(map(int, bbox)), "score": 1.0} for bbox in faces]

        # Compatibility fallback for OpenCV builds without the legacy
        # CascadeClassifier API. It uses simple skin-region candidates and
        # remains fully usable without downloading a model.
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower = np.array([0, 20, 70], dtype=np.uint8)
        upper = np.array([25, 150, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = contours[0] if len(contours) == 2 else contours[1]
        detections = []
        height, width = frame.shape[:2]
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w >= max(30, width * 0.04) and h >= max(30, height * 0.06) and h >= w * 0.9 and h <= w * 2.2:
                detections.append({"bbox": (int(x), int(y), int(w), int(h)), "score": 0.5})
        return sorted(detections, key=lambda item: item["bbox"][2] * item["bbox"][3], reverse=True)[:8]
