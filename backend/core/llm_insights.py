
import json
import os

from groq import Groq


class InsightGenerator:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=api_key) if api_key else None

    def generate_classroom_insight(self, session_data: dict) -> dict:
        """Generate contextual explanations from structured observations."""

        observations = {
            "visible_face_count": session_data.get(
                "visible_face_count", 0
            ),
            "audio_activity_level": session_data.get(
                "audio_activity_level", "unknown"
            ),
            "audio_activity_ratio": session_data.get(
                "audio_activity_ratio"
            ),
            "audio_level_dbfs": session_data.get("audio_level_dbfs"),
            "audio_activity_change": session_data.get(
                "audio_activity_change"
            ),
            "observations": session_data.get("observations", []),
            "rule_recommendations": session_data.get(
                "recommendations", []
            ),
            "limitations": session_data.get("limitations", [])
        }

        fallback = {
            "summary": (
                "Classroom observations were processed using "
                "rule-based audio and visual indicators."
            ),
            "interpretation": (
                "The available measurements describe visible faces "
                "and audio activity, not confirmed attention or learning."
            ),
            "recommendations": observations["rule_recommendations"],
            "evidence": observations["observations"],
            "source": "rule_based_fallback"
        }

        if not self.client:
            return fallback

        prompt = (
            "Analyze these classroom session observations. "
            "Return valid JSON with keys: summary, interpretation, "
            "recommendations (array), and evidence (array of strings). "
            "Be concise, professional, and actionable. Use only the "
            "provided evidence. Do not infer student emotions, attention, "
            "comprehension, identity, or participation from face counts "
            "or audio energy alone. Distinguish measurements from "
            "hypotheses and mention uncertainty where relevant. "
            "Do not invent numerical values.\n\n"
            + json.dumps(observations, ensure_ascii=False)
        )

        try:
            response = self.client.chat.completions.create(
                model=os.getenv(
                    "GROQ_MODEL", "llama-3.3-70b-versatile"
                ),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an educational session analysis "
                            "assistant. Be evidence-based and cautious."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=300,
                response_format={"type": "json_object"}
            )

            result = json.loads(
                response.choices[0].message.content
            )

            # Preserve the original measured evidence and limitations.
            result["evidence"] = observations["observations"]
            result["source"] = "groq_llm"
            result["limitations"] = observations["limitations"]

            return result

        except Exception:
            # Keep the application usable if the API is unavailable.
            return fallback
