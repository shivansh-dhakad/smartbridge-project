
from collections import defaultdict
from datetime import datetime, timezone
from math import hypot


class DataFusionEngine:
    def __init__(self, window_seconds=2.0):
        self.window_seconds = window_seconds
        self.vision_events = []
        self.audio_events = []
        self.session_start = None

        self.participant_history = defaultdict(list)

    def add_vision_event(self, event: dict):
        """
        Expected format:
        {
            "elapsed_seconds": 2.0,
            "participants": [
                {"participant_id": 1, "bbox": [x, y, w, h]}
            ]
        }
        """
        elapsed = float(event["elapsed_seconds"])
        participants = event.get("participants", [])

        normalized = {
            "elapsed_seconds": elapsed,
            "timestamp": event.get(
                "timestamp", datetime.now(timezone.utc).isoformat()
            ),
            "participants": participants
        }

        self.vision_events.append(normalized)

        for participant in participants:
            pid = participant.get("participant_id")
            bbox = participant.get("bbox")

            if pid is None or not bbox or len(bbox) != 4:
                continue

            x, y, w, h = map(float, bbox)

            self.participant_history[pid].append({
                "elapsed_seconds": elapsed,
                "center_x": x + w / 2,
                "center_y": y + h / 2,
                "bbox": [x, y, w, h]
            })

    def add_audio_event(self, event: dict):
        """
        Expected format:
        {
            "elapsed_seconds": 2.0,
            "metrics": {
                "activity_ratio": 0.6,
                "level_dbfs": -24.0,
                "estimated_noise_floor": 0.005
            }
        }
        """
        metrics = event.get("metrics", event)

        self.audio_events.append({
            "elapsed_seconds": float(event["elapsed_seconds"]),
            "timestamp": event.get(
                "timestamp", datetime.now(timezone.utc).isoformat()
            ),
            "metrics": metrics
        })

    def _visual_metrics(self, start, end):
        events = [
            event for event in self.vision_events
            if start <= event["elapsed_seconds"] < end
        ]

        visible_ids = set()
        movement = defaultdict(float)
        previous_positions = {}

        for event in events:
            for participant in event["participants"]:
                pid = participant.get("participant_id")
                bbox = participant.get("bbox")

                if pid is None:
                    continue

                visible_ids.add(pid)

                if not bbox or len(bbox) != 4:
                    continue

                x, y, w, h = map(float, bbox)
                center = (x + w / 2, y + h / 2)

                if pid in previous_positions:
                    px, py = previous_positions[pid]
                    movement[pid] += hypot(
                        center[0] - px, center[1] - py
                    )

                previous_positions[pid] = center

        return {
            "visible_participant_count": len(visible_ids),
            "participant_ids": sorted(visible_ids, key=str),
            "movement_pixels": {
                str(pid): round(distance, 2)
                for pid, distance in movement.items()
            },
            "vision_observation_count": len(events)
        }

    def _audio_metrics(self, start, end):
        events = [
            event for event in self.audio_events
            if start <= event["elapsed_seconds"] < end
        ]

        def mean_metric(key):
            values = [
                float(event["metrics"][key])
                for event in events
                if event["metrics"].get(key) is not None
            ]
            return sum(values) / len(values) if values else None

        return {
            "audio_chunk_count": len(events),
            "mean_activity_ratio": mean_metric("activity_ratio"),
            "mean_level_dbfs": mean_metric("level_dbfs"),
            "mean_noise_floor": mean_metric("estimated_noise_floor")
        }

    def fuse_window(self, start, end):
        visual = self._visual_metrics(start, end)
        audio = self._audio_metrics(start, end)

        # Do not silently treat missing audio as zero activity.
        modalities_available = {
            "vision": visual["vision_observation_count"] > 0,
            "audio": audio["audio_chunk_count"] > 0
        }

        return {
            "window_start_seconds": round(start, 3),
            "window_end_seconds": round(end, 3),
            "visual": visual,
            "audio": audio,
            "modalities_available": modalities_available
        }

    def build_fused_timeline(self, duration_seconds=None):
        all_times = [
            event["elapsed_seconds"]
            for event in self.vision_events + self.audio_events
        ]

        if not all_times:
            return []

        duration = (
            float(duration_seconds)
            if duration_seconds is not None
            else max(all_times) + self.window_seconds
        )

        timeline = []
        start = 0.0

        while start < duration:
            end = min(start + self.window_seconds, duration)
            timeline.append(self.fuse_window(start, end))
            start = end

        return timeline

    def get_session_summary(self):
        timeline = self.build_fused_timeline()

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "window_seconds": self.window_seconds,
            "vision_event_count": len(self.vision_events),
            "audio_event_count": len(self.audio_events),
            "participant_presence": self._presence_summary(),
            "timeline": timeline
        }

    def _presence_summary(self):
        summary = {}

        for pid, records in self.participant_history.items():
            times = sorted(set(
                item["elapsed_seconds"] for item in records
            ))

            # Estimate observed span, not guaranteed continuous presence.
            observed_span = (
                times[-1] - times[0] if len(times) > 1 else 0.0
            )

            summary[str(pid)] = {
                "observed_frames": len(records),
                "first_seen_seconds": times[0] if times else None,
                "last_seen_seconds": times[-1] if times else None,
                "observed_span_seconds": round(observed_span, 3)
            }

        return summary
