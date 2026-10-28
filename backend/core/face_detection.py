
import cv2


class FaceDetector:
    def __init__(self):
        cascade_path = (
            cv2.data.haarcascades
            + "haarcascade_frontalface_default.xml"
        )
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        if self.face_cascade.empty():
            raise RuntimeError("Could not load Haar Cascade classifier")

    def process_frame(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        detections = []

        for x, y, w, h in faces:
            detections.append({
                "bbox": (int(x), int(y), int(w), int(h)),
                "score": 1.0
            })

        return detections
