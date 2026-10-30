import React, { useEffect, useState } from "react";
import AudioCapture from "./components/AudioCapture";
import VisionCapture from "./components/VisionCapture";
import EngagementTimeline from "./components/EngagementTimeline";

const API = `${window.location.protocol}//${window.location.hostname}:8000`;

export default function App() {
  const [active, setActive] = useState(false);
  const [audio, setAudio] = useState(null);
  const [vision, setVision] = useState(null);
  const [session, setSession] = useState(null);
  const [engagement, setEngagement] = useState(null);
  const [apiStatus, setApiStatus] = useState("checking");

  useEffect(() => {
    fetch(`${API}/api/health`).then(r => r.ok ? r.json() : Promise.reject()).then(() => setApiStatus("connected")).catch(() => setApiStatus("offline"));
  }, []);

  useEffect(() => {
    if (!active) return undefined;
    const refresh = async () => {
      try {
        const summary = await fetch(`${API}/api/fusion/session`).then(r => r.json());
        setSession(summary);
        const scoreResponse = await fetch(`${API}/api/engagement/score`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ fused_session: summary, expected_participants: null }) }).then(r => r.json());
        setEngagement(scoreResponse.engagement);
      } catch (error) {
        console.error("Unable to refresh session", error);
      }
    };
    refresh();
    const timer = window.setInterval(refresh, 3000);
    return () => window.clearInterval(timer);
  }, [active]);

  async function resetSession() {
    await fetch(`${API}/api/fusion/reset`, { method: "POST" });
    setSession(null); setEngagement(null); setAudio(null); setVision(null);
  }

  const score = engagement?.session_score;
  const attendees = session ? Object.keys(session.participant_presence).length : 0;
  const suggestions = [];
  if (score != null && score < 40) suggestions.push("Introduce a short interactive question or group activity.");
  if (audio && audio.metrics.activity_ratio < 0.2) suggestions.push("Invite learners to respond or check understanding verbally.");
  if (!vision || vision.participants.length === 0) suggestions.push("Check camera placement and classroom lighting.");
  if (!suggestions.length) suggestions.push("Continue monitoring; the current session indicators are stable.");

  return (
    <div className="app-shell">
      <aside>
        <div className="brand"><span>AI</span><div><strong>Classroom</strong><small>Intelligence</small></div></div>
        <nav><button className="nav-active">Overview</button><button>Attendance</button><button>Engagement</button><button>Insights</button></nav>
        <div className={`api-state ${apiStatus}`}><i /> API {apiStatus}</div>
      </aside>
      <main>
        <header><div><p className="eyebrow">LIVE SESSION</p><h1>Classroom overview</h1></div><div className="header-actions"><button className="secondary" onClick={resetSession}>Reset session</button><button className="primary" onClick={() => setActive(v => !v)}>{active ? "Stop session" : "Start session"}</button></div></header>
        <section className="stats-grid">
          <article><span>Attendance detected</span><strong>{attendees}</strong><small>people tracked</small></article>
          <article><span>Engagement indicator</span><strong>{score == null ? "—" : Math.round(score)}%</strong><small>{engagement?.limitations ? "heuristic score" : "waiting for data"}</small></article>
          <article><span>Audio activity</span><strong>{audio ? `${Math.round(audio.metrics.activity_ratio * 100)}%` : "—"}</strong><small>{audio ? `${audio.metrics.level_dbfs.toFixed(1)} dBFS` : "microphone inactive"}</small></article>
          <article><span>Vision events</span><strong>{session?.vision_event_count ?? 0}</strong><small>{vision ? `${vision.participants.length} visible now` : "camera inactive"}</small></article>
        </section>
        <section className="content-grid">
          <article className="panel camera-card"><div className="panel-heading"><div><p className="eyebrow">CAMERA</p><h2>Live attendance</h2></div><span className={active ? "live" : ""}>{active ? "LIVE" : "OFF"}</span></div><VisionCapture active={active} onVision={setVision} /></article>
          <article className="panel"><div className="panel-heading"><div><p className="eyebrow">AUDIO</p><h2>Room activity</h2></div></div><AudioCapture active={active} onMetrics={setAudio} />{audio && <div className="metric-bars"><div><span>Activity</span><b>{Math.round(audio.metrics.activity_ratio * 100)}%</b><i style={{width: `${audio.metrics.activity_ratio * 100}%`}} /></div><div><span>Signal</span><b>{audio.metrics.level_dbfs.toFixed(1)} dBFS</b></div><div><span>Noise floor</span><b>{audio.metrics.estimated_noise_floor.toFixed(3)}</b></div></div>}</article>
        </section>
        <section className="bottom-grid"><article className="panel"><EngagementTimeline engagement={engagement} /></article><article className="panel suggestions"><div className="panel-heading"><div><p className="eyebrow">ASSISTIVE INSIGHTS</p><h2>Teaching suggestions</h2></div></div>{suggestions.map((item, i) => <div key={i}><span>{i + 1}</span><p>{item}</p></div>)}</article></section>
      </main>
    </div>
  );
}
