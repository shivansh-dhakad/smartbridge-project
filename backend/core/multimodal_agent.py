
from datetime import datetime, timezone


class MultimodalAgent:
    def __init__(self):
        self.previous_audio_activity = None

    def analyze_session(self, vision_data: dict, audio_data: dict) -> dict:
        """
        Combine vision and audio observations using interpretable rules.

        vision_data example:
            {"participants": [{"participant_id": 1, "bbox": (...)}]}

        audio_data example:
            {"activity_ratio": 0.65, "level_dbfs": -24.0,
             "estimated_noise_floor": 0.005}
        """

        participants = vision_data.get("participants", [])
        audio_activity = float(audio_data.get("activity_ratio", 0.0))
        audio_level = float(audio_data.get("level_dbfs", -100.0))
        noise_floor = float(
            audio_data.get("estimated_noise_floor", 0.0)
        )

        observations = []
        recommendations = []

        # Vision observations.
        visible_count = len(participants)

        observations.append({
            "type": "vision",
            "metric": "visible_face_count",
            "value": visible_count,
            "interpretation": (
                "Faces were detected in the current frame."
                if visible_count
                else "No faces were detected in the current frame."
            )
        })

        if visible_count == 0:
            recommendations.append(
                "Check camera positioning, lighting, and visibility."
            )

        # Audio activity observations.
        if audio_activity >= 0.60:
            activity_label = "high"
            observations.append({
                "type": "audio",
                "metric": "estimated_activity",
                "value": audio_activity,
                "interpretation":
                    "High energy-based audio activity was observed."
            })
        elif audio_activity >= 0.20:
            activity_label = "moderate"
            observations.append({
                "type": "audio",
                "metric": "estimated_activity",
                "value": audio_activity,
                "interpretation":
                    "Moderate energy-based audio activity was observed."
            })
        else:
            activity_label = "low"
            observations.append({
                "type": "audio",
                "metric": "estimated_activity",
                "value": audio_activity,
                "interpretation":
                    "Low energy-based audio activity was observed."
            })

        if audio_level > -20:
            recommendations.append(
                "Review audio levels for possible loudness or clipping."
            )

        # Compare activity with the preceding analyzed chunk.
        activity_change = None

        if self.previous_audio_activity is not None:
            activity_change = round(
                audio_activity - self.previous_audio_activity, 3
            )

            if activity_change >= 0.25:
                observations.append({
                    "type": "multimodal",
                    "metric": "audio_activity_change",
                    "value": activity_change,
                    "interpretation":
                        "Audio activity increased substantially."
                })
            elif activity_change <= -0.25:
                observations.append({
                    "type": "multimodal",
                    "metric": "audio_activity_change",
                    "value": activity_change,
                    "interpretation":
                        "Audio activity decreased substantially."
                })

        self.previous_audio_activity = audio_activity

        if noise_floor >= 0.03:
            recommendations.append(
                "Review background sound and microphone placement."
            )

        if not recommendations:
            recommendations.append(
                "Continue monitoring audio and visual indicators "
                "throughout the session."
            )

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "visible_face_count": visible_count,
            "audio_activity_level": activity_label,
            "audio_activity_ratio": audio_activity,
            "audio_level_dbfs": audio_level,
            "estimated_noise_floor": noise_floor,
            "audio_activity_change": activity_change,
            "observations": observations,
            "recommendations": recommendations,
            "limitations": [
                "Visible faces do not establish attention or comprehension.",
                "Audio energy does not establish speech or participation.",
                "This output is an observational estimate, not a "
                "validated student engagement score."
            ]
        }
