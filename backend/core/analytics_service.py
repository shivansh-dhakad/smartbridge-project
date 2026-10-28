
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean, pstdev

from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import (
    SessionLocal,
    Session as SessionModel,
    SessionPerson,
    PersonMetric,
)


class AnalyticsService:
    """
    Generates individual student-facing analytics for a classroom session.

    Analytics include:
    - Timestamp-based engagement trends
    - Attendance duration estimates
    - Engagement consistency
    - High and low engagement-indicator periods
    - Private, individual session summaries

    Scores are descriptive indicators, not grades or validated
    measures of attention, learning, or academic performance.
    """

    def __init__(self, session_factory=None, bucket_seconds=60):
        self.session_factory = session_factory or SessionLocal
        self.bucket_seconds = max(1, int(bucket_seconds))

    @staticmethod
    def _get_value(obj, *names, default=None):
        """Read the first available attribute from a SQLAlchemy model."""
        for name in names:
            if hasattr(obj, name):
                value = getattr(obj, name)
                if value is not None:
                    return value
        return default

    @staticmethod
    def _as_float(value):
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_timestamp(timestamp):
        if timestamp is None:
            return None

        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(
                    timestamp.replace("Z", "+00:00")
                )
            except ValueError:
                return None

        if not isinstance(timestamp, datetime):
            return None

        # Normalize timestamps so subtraction is consistent.
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)

        return timestamp.astimezone(timezone.utc)

    @staticmethod
    def _serialize_timestamp(timestamp):
        if timestamp is None:
            return None
        return timestamp.isoformat()

    def _get_session(self, db, session_id):
        return (
            db.query(SessionModel)
            .filter(SessionModel.id == session_id)
            .first()
        )

    def _get_metrics(self, db, session_id, person_id=None):
        query = db.query(PersonMetric).filter(
            PersonMetric.session_id == session_id
        )

        if person_id is not None:
            if not hasattr(PersonMetric, "person_id"):
                return []

            query = query.filter(
                PersonMetric.person_id == person_id
            )

        timestamp_column = getattr(
            PersonMetric, "timestamp", None
        )

        if timestamp_column is not None:
            query = query.order_by(timestamp_column.asc())

        return query.all()

    def _get_people(self, db, session_id):
        query = db.query(SessionPerson)

        if hasattr(SessionPerson, "session_id"):
            query = query.filter(
                SessionPerson.session_id == session_id
            )

        return query.all()

    def _metric_value(self, metric):
        """
        Support common metric naming conventions.

        Engagement/attention fields are preferred. Emotion or noise
        values are not automatically treated as engagement scores.
        """
        value = self._get_value(
            metric,
            "attention",
            "engagement_score",
            "engagement",
            "attention_score",
            default=None,
        )

        return self._as_float(value)

    def _metric_timestamp(self, metric):
        timestamp = self._get_value(
            metric,
            "timestamp",
            "created_at",
            "recorded_at",
            default=None,
        )

        return self._normalize_timestamp(timestamp)

    def _metric_person_id(self, metric):
        return self._get_value(
            metric,
            "person_id",
            "session_person_id",
            "participant_id",
            default=None,
        )

    def _aggregate_timeline(self, metrics):
        """
        Group records into fixed-duration buckets.

        The first observed metric defines the start of the timeline.
        """
        valid_records = []

        for metric in metrics:
            timestamp = self._metric_timestamp(metric)
            score = self._metric_value(metric)

            if timestamp is None:
                continue

            valid_records.append({
                "timestamp": timestamp,
                "score": score,
            })

        if not valid_records:
            return []

        valid_records.sort(key=lambda item: item["timestamp"])
        origin = valid_records[0]["timestamp"]

        buckets = defaultdict(list)

        for record in valid_records:
            elapsed = (
                record["timestamp"] - origin
            ).total_seconds()

            bucket_index = int(elapsed // self.bucket_seconds)
            buckets[bucket_index].append(record)

        timeline = []

        for index in sorted(buckets):
            records = buckets[index]

            scores = [
                record["score"]
                for record in records
                if record["score"] is not None
                and 0 <= record["score"] <= 100
            ]

            bucket_start = origin + timedelta(
                seconds=index * self.bucket_seconds
            )

            bucket_end = bucket_start + timedelta(
                seconds=self.bucket_seconds
            )

            timeline.append({
                "bucket_index": index,
                "start_seconds": index * self.bucket_seconds,
                "end_seconds": (index + 1) * self.bucket_seconds,
                "start_timestamp": self._serialize_timestamp(
                    bucket_start
                ),
                "end_timestamp": self._serialize_timestamp(
                    bucket_end
                ),
                "average_engagement": (
                    round(mean(scores), 2) if scores else None
                ),
                "observation_count": len(records),
                "scored_observation_count": len(scores),
            })

        return timeline

    @staticmethod
    def _calculate_consistency(scores):
        if not scores:
            return {
                "standard_deviation": None,
                "consistency_label": "insufficient_data",
            }

        deviation = pstdev(scores)

        if deviation <= 10:
            label = "relatively_consistent"
        elif deviation <= 20:
            label = "moderately_variable"
        else:
            label = "highly_variable"

        return {
            "standard_deviation": round(deviation, 2),
            "consistency_label": label,
        }

    def _identify_periods(self, timeline):
        """
        Identify notable high and low engagement-indicator intervals.

        Thresholds are descriptive defaults and can be calibrated
        for the application's scoring method.
        """
        periods = []

        for item in timeline:
            score = item["average_engagement"]

            if score is None:
                continue

            if score >= 75:
                label = "higher_indicator_period"
            elif score < 40:
                label = "lower_indicator_period"
            else:
                continue

            periods.append({
                "type": label,
                "start_seconds": item["start_seconds"],
                "end_seconds": item["end_seconds"],
                "average_engagement": score,
                "description": (
                    "The engagement indicator was relatively high "
                    "during this interval."
                    if label == "higher_indicator_period"
                    else
                    "The engagement indicator was relatively low "
                    "during this interval."
                ),
            })

        return periods

    def _attendance_summary(self, people, metrics):
        """
        Estimate observed attendance span from metric timestamps.

        This is not equivalent to verified continuous attendance.
        """
        timestamps = [
            self._metric_timestamp(metric)
            for metric in metrics
        ]

        timestamps = [
            timestamp for timestamp in timestamps
            if timestamp is not None
        ]

        timestamps.sort()

        if timestamps:
            first_seen = timestamps[0]
            last_seen = timestamps[-1]
            observed_span = max(
                0.0,
                (last_seen - first_seen).total_seconds()
            )
        else:
            first_seen = None
            last_seen = None
            observed_span = None

        return {
            "participant_record_count": len(people),
            "first_observed_at": self._serialize_timestamp(
                first_seen
            ),
            "last_observed_at": self._serialize_timestamp(
                last_seen
            ),
            "observed_span_seconds": (
                round(observed_span, 2)
                if observed_span is not None else None
            ),
            "duration_note": (
                "Observed span between the first and last available "
                "metric timestamps; continuous attendance is not verified."
            ),
        }

    def get_session_trends(self, session_id: int):
        """
        Return aggregate trends for a session.

        This endpoint-level method is useful for dashboards that
        need a session timeline without exposing peer comparisons.
        """
        db = self.session_factory()

        try:
            session = self._get_session(db, session_id)

            if session is None:
                return {
                    "session_id": session_id,
                    "data_available": False,
                    "message": "Session not found.",
                    "timeline": [],
                }

            metrics = self._get_metrics(db, session_id)
            timeline = self._aggregate_timeline(metrics)

            scores = [
                self._metric_value(metric)
                for metric in metrics
            ]

            scores = [
                score for score in scores
                if score is not None and 0 <= score <= 100
            ]

            return {
                "session_id": session_id,
                "data_available": bool(metrics),
                "timeline": timeline,
                "average_engagement": (
                    round(mean(scores), 2) if scores else None
                ),
                "consistency": self._calculate_consistency(scores),
                "notable_periods": self._identify_periods(timeline),
                "observation_count": len(metrics),
            }

        finally:
            db.close()

    def get_student_analytics(
        self,
        session_id: int,
        person_id: int,
    ):
        """
        Return analytics for one participant only.

        No peer ranking or comparative student statistics are returned.
        """
        db = self.session_factory()

        try:
            session = self._get_session(db, session_id)

            if session is None:
                return {
                    "session_id": session_id,
                    "person_id": person_id,
                    "data_available": False,
                    "message": "Session not found.",
                }

            people = self._get_people(db, session_id)

            person_exists = any(
                str(self._get_value(
                    person, "id", "person_id", default=""
                )) == str(person_id)
                for person in people
            )

            # Some schemas link PersonMetric directly to person_id.
            metrics = self._get_metrics(
                db,
                session_id,
                person_id=person_id,
            )

            if not person_exists and not metrics:
                return {
                    "session_id": session_id,
                    "person_id": person_id,
                    "data_available": False,
                    "message": (
                        "No participant records were found for this session."
                    ),
                }

            timeline = self._aggregate_timeline(metrics)

            scores = [
                self._metric_value(metric)
                for metric in metrics
            ]

            scores = [
                score for score in scores
                if score is not None and 0 <= score <= 100
            ]

            return {
                "session_id": session_id,
                "person_id": person_id,
                "data_available": bool(metrics),
                "attendance": self._attendance_summary(
                    [person for person in people
                     if str(self._get_value(
                         person, "id", "person_id", default=""
                     )) == str(person_id)],
                    metrics,
                ),
                "average_engagement": (
                    round(mean(scores), 2) if scores else None
                ),
                "consistency": self._calculate_consistency(scores),
                "timeline": timeline,
                "notable_periods": self._identify_periods(timeline),
                "observation_count": len(metrics),
                "summary": self._build_reflective_summary(
                    scores, timeline
                ),
                "privacy": {
                    "peer_comparison": False,
                    "student_ranking": False,
                    "academic_grade_generated": False,
                },
            }

        finally:
            db.close()

    @staticmethod
    def _build_reflective_summary(scores, timeline):
        if not scores:
            return [
                "Not enough engagement observations are available yet."
            ]

        summary = [
            "This report describes observed engagement indicators "
            "to support personal reflection.",
        ]

        average_score = mean(scores)

        if average_score >= 75:
            summary.append(
                "The recorded indicator was relatively high on average."
            )
        elif average_score < 40:
            summary.append(
                "The recorded indicator was relatively low on average. "
                "Review the timeline and session context before drawing "
                "conclusions."
            )
        else:
            summary.append(
                "The recorded indicator varied around a moderate range."
            )

        valid_windows = [
            item for item in timeline
            if item["average_engagement"] is not None
        ]

        if len(valid_windows) >= 2:
            first_score = valid_windows[0]["average_engagement"]
            last_score = valid_windows[-1]["average_engagement"]

            if last_score > first_score:
                summary.append(
                    "The indicator was higher in the final observed "
                    "window than in the first."
                )
            elif last_score < first_score:
                summary.append(
                    "The indicator was lower in the final observed "
                    "window than in the first."
                )
            else:
                summary.append(
                    "The first and final observed windows had the "
                    "same indicator value."
                )

        return summary
