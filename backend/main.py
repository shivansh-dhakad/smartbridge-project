
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from core.data_fusion import DataFusionEngine
from core.engagement_scorer import EngagementScorer

app = FastAPI(title="Classroom Engagement System")

fusion_engine = DataFusionEngine(window_seconds=2.0)
engagement_scorer = EngagementScorer()


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
    expected_participants: int | None = Field(
        default=None, ge=1
    )


@app.get("/")
def root():
    return {
        "message": "Classroom Engagement System API",
        "endpoints": [
            "/api/fusion/vision",
            "/api/fusion/audio",
            "/api/fusion/session",
            "/api/fusion/reset",
            "/api/engagement/score",
        ],
    }


@app.post("/api/fusion/vision")
def add_vision_event(event: VisionEvent):
    try:
        fusion_engine.add_vision_event(event.model_dump())
        return {
            "status": "accepted",
            "modality": "vision",
        }
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc


@app.post("/api/fusion/audio")
def add_audio_event(event: AudioEvent):
    try:
        fusion_engine.add_audio_event(event.model_dump())
        return {
            "status": "accepted",
            "modality": "audio",
        }
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc


@app.get("/api/fusion/session")
def get_fused_session():
    return fusion_engine.get_session_summary()


@app.post("/api/fusion/reset")
def reset_fusion_session():
    global fusion_engine
    fusion_engine = DataFusionEngine(window_seconds=2.0)

    return {"status": "reset"}


@app.post("/api/engagement/score")
def calculate_engagement(request: EngagementScoreRequest):
    try:
        result = engagement_scorer.score_session(
            request.fused_session,
            expected_participants=request.expected_participants,
        )

        return {
            "status": "success",
            "engagement": result,
        }

    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc
