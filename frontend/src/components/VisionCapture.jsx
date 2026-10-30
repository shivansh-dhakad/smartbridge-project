import React, { useEffect, useRef, useState } from "react";

const websocketUrl = () => `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.hostname}:8000/ws/vision`;

export default function VisionCapture({ active, onVision }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState("");

  useEffect(() => {
    if (!active) return undefined;
    let cancelled = false;

    async function start() {
      try {
        setError("");
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
        if (cancelled) { stream.getTracks().forEach(track => track.stop()); return; }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;

        const ws = new WebSocket(websocketUrl());
        wsRef.current = ws;
        ws.onmessage = event => {
          const data = JSON.parse(event.data);
          if (data.preview) setPreview(data.preview);
          if (data.event === "vision_metrics") onVision?.(data);
        };
        ws.onerror = () => setError("Unable to connect to the vision server.");
        await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });

        timerRef.current = window.setInterval(() => {
          const video = videoRef.current;
          const canvas = canvasRef.current;
          if (!video || !canvas || video.readyState < 2 || ws.readyState !== WebSocket.OPEN) return;
          canvas.width = Math.min(640, video.videoWidth);
          canvas.height = Math.round(canvas.width * video.videoHeight / video.videoWidth);
          canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
          ws.send(canvas.toDataURL("image/jpeg", 0.72).split(",")[1]);
        }, 700);
      } catch (err) {
        setError(err.message || "Camera access failed. Allow camera permission and try again.");
      }
    }
    start();
    return () => {
      cancelled = true;
      if (timerRef.current) window.clearInterval(timerRef.current);
      wsRef.current?.close();
      wsRef.current = null;
      streamRef.current?.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    };
  }, [active]);

  return (
    <div className="camera-panel">
      <video ref={videoRef} autoPlay muted playsInline className={preview ? "source-video hidden-video" : "source-video"} />
      <canvas ref={canvasRef} hidden />
      {preview ? <img src={preview} alt="Live face detection" className="camera-preview" /> : <div className="camera-placeholder">Camera preview</div>}
      {error && <p className="error" role="alert">{error}</p>}
    </div>
  );
}
