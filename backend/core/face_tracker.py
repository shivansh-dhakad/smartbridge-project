
class FaceTracker:
    def __init__(self, iou_threshold=0.3, max_missed=10):
        self.iou_threshold = iou_threshold
        self.max_missed = max_missed
        self.next_id = 1
        self.tracks = {}

    @staticmethod
    def calculate_iou(box1, box2):
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2

        left = max(x1, x2)
        top = max(y1, y2)
        right = min(x1 + w1, x2 + w2)
        bottom = min(y1 + h1, y2 + h2)

        intersection = max(0, right - left) * max(0, bottom - top)

        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection

        return intersection / union if union else 0.0

    def update(self, detections):
        # Mark existing tracks as temporarily missed.
        for track in self.tracks.values():
            track["missed"] += 1

        unmatched = set(self.tracks.keys())
        assignments = []

        # Match each detection to the best overlapping track.
        for detection in detections:
            bbox = detection["bbox"]
            best_id = None
            best_iou = 0.0

            for track_id in unmatched:
                iou = self.calculate_iou(
                    bbox, self.tracks[track_id]["bbox"]
                )

                if iou > best_iou:
                    best_iou = iou
                    best_id = track_id

            if best_id is not None and best_iou >= self.iou_threshold:
                track_id = best_id
                unmatched.remove(track_id)

                self.tracks[track_id]["bbox"] = bbox
                self.tracks[track_id]["missed"] = 0
            else:
                track_id = self.next_id
                self.next_id += 1

                self.tracks[track_id] = {
                    "bbox": bbox,
                    "missed": 0
                }

            assignments.append({
                "participant_id": track_id,
                "bbox": bbox,
                "score": detection.get("score", 1.0)
            })

        # Remove tracks that have been missing too long.
        expired = [
            track_id
            for track_id, track in self.tracks.items()
            if track["missed"] > self.max_missed
        ]

        for track_id in expired:
            del self.tracks[track_id]

        return assignments
