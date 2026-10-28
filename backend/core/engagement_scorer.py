
from dataclasses import dataclass


@dataclass
class ScoringConfig:
    presence_weight: float = 0.40
    movement_weight: float = 0.15
    audio_weight: float = 0.45

    # Movement is measured in pixels per window.
    movement_reference_pixels: float = 100.0

    # Consecutive low-indicator duration before flagging a period.
    low_score_threshold: float = 30.0
    low_duration_seconds: float = 30.0


class EngagementScorer:
    def __init__(self, config=None):
        self.config = config or ScoringConfig()

        weights = [
            self.config.presence_weight,
            self.config.movement_weight,
            self.config.audio_weight
        ]

        if any(weight < 0 for weight in weights) or sum(weights) <= 0:
            raise ValueError("Scoring weights must be non-negative, with a positive sum")

    @staticmethod
    def _clamp(value, minimum=0.0, maximum=1.0):
        return max(minimum, min(maximum, value))

    def _score_window(self, window, expected_participants=None):
        visual = window.get("visual", {})
        audio = window.get("audio", {})
        available = window.get("modalities_available", {})

        # Missing data is not equivalent to zero engagement.
        presence_available = available.get("vision", False)
        audio_available = available.get("audio", False)

        visible_count = visual.get("visible_participant_count", 0)

        if expected_participants and expected_participants > 0:
            presence = self._clamp(
                visible_count / expected_participants
            )
        else:
            # Without an expected count, only presence availability
            # can be assessed, not classroom-wide attendance.
            presence = 1.0 if visible_count > 0 else 0.0

        movement_by_person = visual.get("movement_pixels", {})
        movement_pixels = (
            sum(movement_by_person.values())
            if movement_by_person else None
        )

        if movement_pixels is not None:
            movement = self._clamp(
                movement_pixels /
                max(self.config.movement_reference_pixels, 1.0)
            )
        else:
            movement = None

        audio_activity = audio.get("mean_activity_ratio")
        if audio_activity is not None:
            audio_activity = self._clamp(float(audio_activity))

        # Renormalize using only available signals.
        components = []

        if presence_available:
            components.append(
                (self.config.presence_weight, presence)
            )

        if movement is not None and presence_available:
            components.append(
                (self.config.movement_weight, movement)
            )

        if audio_available and audio_activity is not None:
            components.append(
                (self.config.audio_weight, audio_activity)
            )

        total_weight = sum(weight for weight, _ in components)

        if total_weight == 0:
            score = None
        else:
            score = round(
                100 * sum(
                    weight * value for weight, value in components
                ) / total_weight,
                2
            )

        if score is None:
            label = "insufficient_data"
        elif score >= 70:
            label = "high_indicator"
        elif score >= 40:
            label = "moderate_indicator"
        else:
            label = "low_indicator"

        return {
            "start_seconds": window["window_start_seconds"],
            "end_seconds": window["window_end_seconds"],
            "score": score,
            "label": label,
            "components": {
                "visual_presence": (
                    round(presence * 100, 2)
                    if presence_available else None
                ),
                "movement_activity": (
                    round(movement * 100, 2)
                    if movement is not None and presence_available
                    else None
                ),
                "audio_activity": (
                    round(audio_activity * 100, 2)
                    if audio_available and audio_activity is not None
                    else None
                )
            },
            "modalities_available": available
        }

    def score_session(self, fused_session, expected_participants=None):
        timeline = fused_session.get("timeline", [])
        scored_windows = []

        for window in timeline:
            scored_windows.append(
                self._score_window(
                    window,
                    expected_participants=expected_participants
                )
            )

        # Identify contiguous low-indicator intervals.
        low_periods = []
        period_start = None
        period_end = None

        for item in scored_windows:
            is_low = (
                item["score"] is not None
                and item["score"] < self.config.low_score_threshold
            )

            if is_low:
                if period_start is None:
                    period_start = item["start_seconds"]

                period_end = item["end_seconds"]
            elif period_start is not None:
                duration = period_end - period_start

                if duration >= self.config.low_duration_seconds:
                    low_periods.append({
                        "start_seconds": period_start,
                        "end_seconds": period_end,
                        "duration_seconds": duration
                    })

                period_start = None
                period_end = None

        if period_start is not None:
            duration = period_end - period_start

            if duration >= self.config.low_duration_seconds:
                low_periods.append({
                    "start_seconds": period_start,
                    "end_seconds": period_end,
                    "duration_seconds": duration
                })

        valid = [
            item for item in scored_windows
            if item["score"] is not None
        ]

        peak = max(valid, key=lambda item: item["score"], default=None)
        mean_score = (
            round(sum(item["score"] for item in valid) / len(valid), 2)
            if valid else None
        )

        return {
            "session_score": mean_score,
            "scoring_method": "weighted_rule_based_indicator",
            "window_count": len(scored_windows),
            "scored_window_count": len(valid),
            "timeline": scored_windows,
            "peak_period": peak,
            "low_indicator_periods": low_periods,
            "limitations": [
                "Scores are heuristic indicators, not validated measures of attention.",
                "Movement and audio activity do not necessarily indicate engagement.",
                "Expected participant count is needed to estimate relative presence.",
                "Missing modality data is excluded rather than treated as zero."
            ]
        }
