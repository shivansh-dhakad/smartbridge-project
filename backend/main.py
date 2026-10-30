
import base64
import time
from datetime import datetime, timezone

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.audio_service import AudioService
from core.data_fusion import DataFusionEngine
from core.engagement_scorer import EngagementScorer
from core.face_detection import FaceDetector
from core.face_tracker import FaceTracker
from core.multimodal_agent import MultimodalAgent

app = FastAPI(title="Multimodal Classroom Engagement API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fusion_engine = DataFusionEngine(window_seconds=2.0)
engagement_scorer = EngagementScorer()
audio_service = AudioService(sample_rate=16000)
multimodal_agent = MultimodalAgent()
face_detector = FaceDetector()
face_tracker = FaceTracker()
session_started_at = time.monotonic()


class VisionEvent(BaseModel):
    elapsed_seconds: float = Field(ge=0)
    timestamp: str | None = None
    participants: list[dict] = Field(default_factory=list)


class AudioEvent(BaseModel):
    elapsed_seconds: float = Field(ge=0)
    timestamp: str | None = None
    metrics: dict = Field(default_factory=dict)


class EngagementScoreRequest(BaseModel):
    fused_session: dict
    expected_participants: int | None = Field(default=None, ge=1)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": app.title}


@app.get("/")
def root():
    return {"message": "Multimodal Classroom Engagement API", "docs": "/docs", "health": "/api/health"}


@app.post("/api/fusion/vision")
def add_vision_event(event: VisionEvent):
    fusion_engine.add_vision_event(event.model_dump())
    return {"status": "accepted", "modality": "vision"}


@app.post("/api/fusion/audio")
def add_audio_event(event: AudioEvent):
    fusion_engine.add_audio_event(event.model_dump())
    return {"status": "accepted", "modality": "audio"}


@app.get("/api/fusion/session")
def get_fused_session():
    return fusion_engine.get_session_summary()


@app.post("/api/fusion/reset")
def reset_fusion_session():
    global fusion_engine, face_tracker, multimodal_agent, session_started_at
    fusion_engine = DataFusionEngine(window_seconds=2.0)
    face_tracker = FaceTracker()
    multimodal_agent = MultimodalAgent()
    session_started_at = time.monotonic()
    return {"status": "reset"}


@app.post("/api/engagement/score")
def calculate_engagement(request: EngagementScoreRequest):
    result = engagement_scorer.score_session(request.fused_session, request.expected_participants)
    return {"status": "success", "engagement": result}


@app.websocket("/ws/audio")
async def audio_socket(websocket: WebSocket):
    await websocket.accept()
    start = time.monotonic()
    try:
        while True:
            audio_bytes = await websocket.receive_bytes()
            metrics = audio_service.process_pcm_bytes(audio_bytes)
            if metrics:
                elapsed = round(time.monotonic() - start, 2)
                event = {"elapsed_seconds": elapsed, "timestamp": datetime.now(timezone.utc).isoformat(), "metrics": metrics}
                fusion_engine.add_audio_event(event)
                await websocket.send_json({"event": "audio_metrics", "elapsed_seconds": elapsed, "metrics": metrics})
    except WebSocketDisconnect:
        pass
    except ValueError as exc:
        await websocket.close(code=1003, reason=str(exc))


@app.websocket("/ws/vision")
async def vision_socket(websocket: WebSocket):
    await websocket.accept()
    start = time.monotonic()
    try:
        while True:
            payload = await websocket.receive_text()
            if payload.startswith("data:image"):
                payload = payload.split(",", 1)[1]
            encoded = base64.b64decode(payload)
            frame = cv2.imdecode(np.frombuffer(encoded, np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                await websocket.send_json({"event": "error", "message": "Invalid image frame"})
                continue
            detections = face_detector.process_frame(frame)
            tracks = face_tracker.update(detections)
            elapsed = round(time.monotonic() - start, 2)
            participants = [{"participant_id": track["participant_id"], "bbox": [*track["bbox"]]} for track in tracks]
            fusion_engine.add_vision_event({"elapsed_seconds": elapsed, "timestamp": datetime.now(timezone.utc).isoformat(), "participants": participants})
            for track in tracks:
                x, y, w, h = track["bbox"]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (34, 197, 94), 2)
                cv2.putText(frame, f"Person {track['participant_id']}", (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (34, 197, 94), 2)
            success, jpg = cv2.imencode(".jpg", frame)
            preview = "data:image/jpeg;base64," + base64.b64encode(jpg).decode() if success else None
            await websocket.send_json({"event": "vision_metrics", "elapsed_seconds": elapsed, "participants": participants, "preview": preview})
    except WebSocketDisconnect:
        pass
    except (ValueError, cv2.error) as exc:
        await websocket.close(code=1003, reason=str(exc))
