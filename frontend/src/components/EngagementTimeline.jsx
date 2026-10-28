
import React from "react";

export default function EngagementTimeline({ engagement }) {
  if (!engagement) {
    return <p>Waiting for engagement analysis...</p>;
  }

  return (
    <section>
      <h2>Engagement Indicators</h2>

      <p>
        Session average:{" "}
        {engagement.session_score == null
          ? "Insufficient data"
          : `${engagement.session_score.toFixed(1)} / 100`}
      </p>

      <div>
        {engagement.timeline.map((item, index) => (
          <div
            key={`${item.start_seconds}-${index}`}
            style={{
              border: "1px solid #ccc",
              borderRadius: 8,
              padding: 12,
              marginBottom: 8
            }}
          >
            <strong>
              {item.start_seconds}s–{item.end_seconds}s
            </strong>

            <p>
              Score:{" "}
              {item.score == null
                ? "Insufficient data"
                : `${item.score}/100`}
            </p>

            <p>
              Level: {item.label.replaceAll("_", " ")}
            </p>
          </div>
        ))}
      </div>

      <h3>Low-indicator periods</h3>

      {engagement.low_indicator_periods.length === 0 ? (
        <p>No extended low-indicator period was detected.</p>
      ) : (
        engagement.low_indicator_periods.map((period, index) => (
          <p key={index}>
            {period.start_seconds}s–{period.end_seconds}s
            {" "}({period.duration_seconds}s)
          </p>
        ))
      )}
    </section>
  );
}
