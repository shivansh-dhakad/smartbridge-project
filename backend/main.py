
import time
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from core.audio_service import AudioService

app = FastAPI(title="Classroom Engagement System")


@app.websocket("/ws/audio")
async def audio_stream(websocket: WebSocket):
    await websocket.accept()

    service = AudioService(sample_rate=16000)
    session_start = time.monotonic()

    total_audio_seconds = 0.0
    active_seconds = 0.0
    chunk_count = 0
    rms_values = []
    noise_values = []

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            audio_bytes = message.get("bytes")

            if not audio_bytes:
                continue

            metrics = service.process_pcm_bytes(audio_bytes)

            if metrics is None:
                continue

            chunk_count += 1
            total_audio_seconds += metrics["duration_seconds"]
            active_seconds += metrics["estimated_active_seconds"]
            rms_values.append(metrics["rms_amplitude"])
            noise_values.append(metrics["estimated_noise_floor"])

            await websocket.send_json({
                "event": "audio_metrics",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": round(
                    time.monotonic() - session_start, 3
                ),
                "metrics": metrics
            })

    except WebSocketDisconnect:
        pass

    finally:
        summary = {
            "event": "session_audio_summary",
            "chunks_processed": chunk_count,
            "total_audio_seconds": round(total_audio_seconds, 3),
            "estimated_active_seconds": round(active_seconds, 3),
            "mean_rms_amplitude": (
                sum(rms_values) / len(rms_values) if rms_values else 0.0
            ),
            "mean_estimated_noise_floor": (
                sum(noise_values) / len(noise_values)
                if noise_values else 0.0
            )
        }

        # The connection may already be closed; summary is also logged.
        print(summary)


@app.get("/")
def root():
    return {"message": "Classroom Engagement System API"}
