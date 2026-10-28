
class RecommendationsEngine:
    """
    Generates non-prescriptive, rule-based teaching recommendations.

    Input:
        Session status containing participant indicators, engagement
        timeline, audio activity, and optional noise measurements.

    Output:
        List of recommendations containing type, message, reason,
        and supporting evidence.
    """

    def __init__(
        self,
        individual_attention_threshold=40,
        global_attention_threshold=60,
        low_engagement_threshold=40,
        high_engagement_threshold=75,
        high_noise_threshold_dbfs=-20,
        sustained_period_seconds=30,
    ):
        self.individual_attention_threshold = (
            individual_attention_threshold
        )
        self.global_attention_threshold = global_attention_threshold
        self.low_engagement_threshold = low_engagement_threshold
        self.high_engagement_threshold = high_engagement_threshold
        self.high_noise_threshold_dbfs = high_noise_threshold_dbfs
        self.sustained_period_seconds = sustained_period_seconds

    @staticmethod
    def _number(value):
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _recommendation(
        recommendation_type,
        message,
        reason,
        evidence=None,
    ):
        return {
            "type": recommendation_type,
            "message": message,
            "reason": reason,
            "evidence": evidence or {},
        }

    def _participant_recommendations(self, people):
        recommendations = []

        for person in people:
            attention = self._number(person.get("attention"))

            if attention is None:
                continue

            if attention < self.individual_attention_threshold:
                participant_id = person.get(
                    "id", person.get("participant_id", "unknown")
                )

                recommendations.append(
                    self._recommendation(
                        "alert",
                        (
                            f"Participant {participant_id} has a "
                            f"low attention indicator ({attention:.1f}%). "
                            "Consider checking whether clarification, "
                            "a short question, or additional support "
                            "would be helpful."
                        ),
                        "The participant attention indicator is below "
                        "the configured threshold.",
                        {
                            "participant_id": participant_id,
                            "attention_indicator": attention,
                            "threshold": (
                                self.individual_attention_threshold
                            ),
                        },
                    )
                )

        return recommendations

    def _global_attention_recommendation(self, people):
        attention_values = [
            self._number(person.get("attention"))
            for person in people
        ]

        attention_values = [
            value for value in attention_values
            if value is not None
        ]

        if len(attention_values) < 3:
            return None

        average = sum(attention_values) / len(attention_values)

        if average < self.global_attention_threshold:
            return self._recommendation(
                "warning",
                (
                    "The average participant attention indicator is "
                    f"{average:.1f}%. Consider a brief recap, an "
                    "interactive question, or a change in activity."
                ),
                "The average available participant indicators are "
                "below the configured classroom threshold.",
                {
                    "average_attention_indicator": round(average, 2),
                    "participants_assessed": len(attention_values),
                    "threshold": self.global_attention_threshold,
                },
            )

        return None

    def _timeline_recommendations(self, timeline):
        recommendations = []

        valid_windows = [
            window for window in timeline
            if self._number(window.get("score")) is not None
        ]

        if not valid_windows:
            return recommendations

        # Detect consecutive low-scoring windows.
        period_start = None
        period_end = None

        def close_low_period():
            if period_start is None:
                return

            duration = period_end - period_start

            if duration >= self.sustained_period_seconds:
                recommendations.append(
                    self._recommendation(
                        "warning",
                        (
                            "A sustained low engagement indicator was "
                            f"observed from {period_start:.1f}s to "
                            f"{period_end:.1f}s. Consider a short "
                            "interactive activity, a comprehension check, "
                            "or a change of pace."
                        ),
                        "The engagement indicator remained below "
                        "the configured threshold for an extended period.",
                        {
                            "start_seconds": period_start,
                            "end_seconds": period_end,
                            "duration_seconds": duration,
                            "threshold": self.low_engagement_threshold,
                        },
                    )
                )

        for window in valid_windows:
            score = float(window["score"])
            start = float(window["start_seconds"])
            end = float(window["end_seconds"])

            if score < self.low_engagement_threshold:
                if period_start is None:
                    period_start = start

                period_end = end

            else:
                close_low_period()
                period_start = None
                period_end = None

        close_low_period()

        # Identify the peak scoring interval.
        peak = max(
            valid_windows,
            key=lambda window: float(window["score"]),
        )

        if float(peak["score"]) >= self.high_engagement_threshold:
            recommendations.append(
                self._recommendation(
                    "info",
                    (
                        "A relatively high engagement indicator was "
                        f"observed between {peak['start_seconds']}s "
                        f"and {peak['end_seconds']}s. Review the "
                        "teaching activity used during this interval "
                        "to identify approaches worth repeating."
                    ),
                    "This interval had the highest score among the "
                    "available timeline windows and exceeded the "
                    "configured high-indicator threshold.",
                    {
                        "start_seconds": peak["start_seconds"],
                        "end_seconds": peak["end_seconds"],
                        "score": peak["score"],
                    },
                )
            )

        return recommendations

    def _audio_recommendations(self, session_status):
        recommendations = []

        timeline = session_status.get("timeline", [])

        for window in timeline:
            audio = window.get("audio", {})
            available = window.get("modalities_available", {})

            if not available.get("audio", False):
                continue

            noise_level = self._number(audio.get("mean_level_dbfs"))

            if (
                noise_level is not None
                and noise_level > self.high_noise_threshold_dbfs
            ):
                recommendations.append(
                    self._recommendation(
                        "warning",
                        (
                            "Elevated audio levels were detected between "
                            f"{window.get('start_seconds', window.get('window_start_seconds'))}s "
                            "and "
                            f"{window.get('end_seconds', window.get('window_end_seconds'))}s. "
                            "Consider checking whether background noise "
                            "is affecting audibility."
                        ),
                        "The measured audio level exceeded the configured "
                        "threshold.",
                        {
                            "mean_level_dbfs": noise_level,
                            "threshold_dbfs": (
                                self.high_noise_threshold_dbfs
                            ),
                        },
                    )
                )

        return recommendations

    def generate_realtime_recommendations(self, session_status: dict):
        """
        Generate suggestions from the current classroom session.

        Supported inputs:
            people: [{"id": 1, "attention": 35}, ...]
            timeline: fused or scored engagement timeline
            engagement: engagement scorer output
        """
        recommendations = []

        people = session_status.get("people", [])

        recommendations.extend(
            self._participant_recommendations(people)
        )

        global_recommendation = (
            self._global_attention_recommendation(people)
        )

        if global_recommendation:
            recommendations.append(global_recommendation)

        engagement = session_status.get("engagement", {})
        timeline = session_status.get("timeline")

        if timeline is None:
            timeline = engagement.get("timeline", [])

        recommendations.extend(
            self._timeline_recommendations(timeline)
        )

        recommendations.extend(
            self._audio_recommendations(session_status)
        )

        if not recommendations:
            recommendations.append(
                self._recommendation(
                    "info",
                    (
                        "There are no current rule-based alerts. "
                        "Continue monitoring the session and review "
                        "the engagement timeline periodically."
                    ),
                    "No configured recommendation rule was triggered "
                    "by the available data.",
                )
            )

        return recommendations
