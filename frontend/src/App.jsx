import React, { useState } from "react";
import AudioCapture from "./components/AudioCapture";

export default function App() {
  const [active, setActive] = useState(false);
  const [latestMetrics, setLatestMetrics] = useState(null);

  return (
    <main>
      <h1>Classroom Audio Analysis</h1>

      <button onClick={() => setActive(value => !value)}>
        {active ? "Stop Analysis" : "Start Analysis"}
      </button>

      <AudioCapture
        active={active}
        onMetrics={setLatestMetrics}
      />

      {latestMetrics && (
        <section>
          <h2>Live Audio Metrics</h2>
          <p>
            Signal level:{" "}
            {latestMetrics.metrics.level_dbfs.toFixed(2)} dBFS
          </p>
          <p>
            Activity ratio:{" "}
            {(latestMetrics.metrics.activity_ratio * 100).toFixed(1)}%
          </p>
          <p>
            Estimated noise floor:{" "}
            {latestMetrics.metrics.estimated_noise_floor.toFixed(4)}
          </p>
        </section>
      )}
    </main>
  );
}
