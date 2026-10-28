
from fastapi import HTTPException
from pydantic import BaseModel, Field

from core.data_fusion import DataFusionEngine

fusion_engine = DataFusionEngine(window_seconds=2.0)


class VisionEvent(BaseModel):
    elapsed_seconds: float = Field(ge=0)
    timestamp: str | None = None
    participants: list[dict] = Field(default_factory=list)


class AudioEvent(BaseModel):
    elapsed_seconds: float = Field(ge=0)
    timestamp: str | None = None
    metrics: dict = Field(default_factory=dict)


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
    global fusion_engine
    fusion_engine = DataFusionEngine(window_seconds=2.0)
    return {"status": "reset"}
