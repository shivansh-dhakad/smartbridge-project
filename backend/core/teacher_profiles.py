
from collections import defaultdict
from statistics import mean


class TeacherProfileService:
    """
    Builds teacher profiles from supplied classroom session records.

    Each session may contain:
        teacher_id
        session_id
        name
        engagement_score
        timestamp
        participant_trends
    """

    def __init__(self, session_provider=None):
        self.session_provider = session_provider

    def _get_sessions(self, teacher_id):
        if self.session_provider is None:
            return []

        if callable(self.session_provider):
            sessions = self.session_provider(teacher_id)
        else:
            sessions = self.session_provider

        return [
            session for session in sessions
            if str(session.get("teacher_id")) == str(teacher_id)
        ]

    @staticmethod
    def _score(session):
        value = session.get("engagement_score")

        if value is None:
            value = session.get("session_score")

        try:
            value = float(value)
        except (TypeError, ValueError):
            return None

        return value if 0 <= value <= 100 else None

    @staticmethod
    def _session_name(session, index):
        return session.get(
            "name",
            session.get(
                "session_name",
                f"Session {index + 1}",
            ),
        )

    @staticmethod
    def _session_timestamp(session):
        return (
            session.get("timestamp")
            or session.get("created_at")
            or session.get("date")
            or ""
        )

    @staticmethod
    def _trend_status(change):
        if change > 0:
            return "improved"
        if change < 0:
            return "declining"
        return "stable"

    def _student_trends(self, sessions):
        history = defaultdict(list)

        for session in sessions:
            participants = session.get(
                "participant_trends",
                session.get("student_trends", []),
            )

            for participant in participants:
                name = participant.get(
                    "name",
                    participant.get("participant_id", "Unknown"),
                )

                value = participant.get(
                    "attention",
                    participant.get("engagement_score"),
                )

                try:
                    value = float(value)
                except (TypeError, ValueError):
                    continue

                history[str(name)].append(value)

        trends = []

        for name, values in history.items():
            if len(values) < 2:
                change = 0.0
            else:
                change = values[-1] - values[0]

            trends.append({
                "name": name,
                "change": round(change, 2),
                "status": self._trend_status(change),
                "latest_indicator": round(values[-1], 2),
                "observations": len(values),
            })

        return trends

    def _strengths_and_improvements(self, scores, trends):
        strengths = []
        improvements = []

        if scores:
            average_score = mean(scores)

            if average_score >= 75:
                strengths.append(
                    "High average engagement indicator across recorded sessions"
                )
            elif average_score >= 60:
                strengths.append(
                    "Moderate average engagement indicator across recorded sessions"
                )
            else:
                improvements.append(
                    "Review sessions with consistently low engagement indicators"
                )

            if len(scores) >= 2 and scores[-1] > scores[0]:
                strengths.append(
                    "Recorded session engagement indicator is trending upward"
                )
            elif len(scores) >= 2 and scores[-1] < scores[0]:
                improvements.append(
                    "Review the causes of declining session indicators"
                )

        improving = sum(
            trend["status"] == "improved" for trend in trends
        )
        declining = sum(
            trend["status"] == "declining" for trend in trends
        )

        if improving:
            strengths.append(
                f"{improving} participant trend(s) show an increase"
            )

        if declining:
            improvements.append(
                f"Review {declining} participant trend(s) showing a decrease"
            )

        if not scores:
            improvements.append(
                "Record classroom sessions to establish a reliable baseline"
            )

        if not trends:
            improvements.append(
                "Collect participant-level observations before generating individual trends"
            )

        return strengths, improvements

    def get_profile(self, teacher_id: str):
        sessions = self._get_sessions(teacher_id)

        # Sort chronologically when timestamps are available.
        sessions.sort(key=self._session_timestamp)

        valid_sessions = []
        scores = []

        for index, session in enumerate(sessions):
            score = self._score(session)

            if score is None:
                continue

            scores.append(score)

            valid_sessions.append({
                "name": self._session_name(session, index),
                "engagement": round(score, 2),
                "timestamp": self._session_timestamp(session),
                "session_id": session.get("session_id"),
            })

        effectiveness_score = (
            round(mean(scores), 2) if scores else None
        )

        trend_change = (
            round(scores[-1] - scores[0], 2)
            if len(scores) >= 2 else None
        )

        student_trends = self._student_trends(sessions)

        strengths, improvements = self._strengths_and_improvements(
            scores,
            student_trends,
        )

        return {
            "teacher_id": str(teacher_id),
            "effectiveness_score": effectiveness_score,
            "trend": trend_change,
            "class_history": valid_sessions,
            "student_trends": student_trends,
            "strengths": strengths,
            "areas_for_improvement": improvements,
            "total_sessions": len(sessions),
            "scored_sessions": len(valid_sessions),
            "data_available": bool(valid_sessions),
            "notice": (
                "These summaries describe heuristic engagement indicators, "
                "not validated measures of teaching effectiveness or student learning."
            ),
        }
