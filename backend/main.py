
from fastapi import HTTPException
from pydantic import BaseModel, Field

from core.multimodal_agent import MultimodalAgent
from core.llm_insights import InsightGenerator


multimodal_agent = MultimodalAgent()
insight_generator = InsightGenerator()


class SessionAnalysisRequest(BaseModel):
    vision_data: dict = Field(default_factory=dict)
    audio_data: dict = Field(default_factory=dict)


@app.post("/api/insights")
def generate_insights(request: SessionAnalysisRequest):
    try:
        analysis = multimodal_agent.analyze_session(
            vision_data=request.vision_data,
            audio_data=request.audio_data
        )

        insight = insight_generator.generate_classroom_insight(
            analysis
        )

        return {
            "status": "success",
            "analysis": analysis,
            "insight": insight
        }

    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc
