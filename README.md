# Multimodal Attendance & Engagement Agent

A complete, privacy-conscious classroom dashboard that combines browser microphone activity and camera face detection with offline, rule-based engagement analysis.

## Features

- Live webcam-based face detection and attendance tracking
- Sustained-presence history and timestamped session data
- Live microphone activity, signal level, and noise-floor analysis
- Multimodal engagement timeline with attendance and audio indicators
- Context-aware teaching suggestions
- FastAPI documentation and WebSocket endpoints
- Responsive React dashboard
- No cloud API or external AI service is required

> Engagement values are heuristic indicators, not validated measures of attention, learning, or academic performance. Keep camera and microphone consent clear and visible for every participant.

## Requirements

- Python 3.10–3.12
- Node.js 18 or newer
- A webcam and microphone for live collection
- Windows, macOS, or Linux

## Start the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API documentation is available at `http://localhost:8000/docs` and health status at `http://localhost:8000/api/health`.

## Start the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, then click **Start session** and allow camera and microphone permissions.

## Production build

```powershell
cd frontend
npm run build
```

The static site is written to `frontend/dist`. For the recommended local setup, serve it with Vite (`npm run dev`) and keep the API running on port 8000.

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Backend health check |
| GET | `/api/fusion/session` | Current fused session summary |
| POST | `/api/fusion/vision` | Add a structured vision observation |
| POST | `/api/fusion/audio` | Add a structured audio observation |
| POST | `/api/fusion/reset` | Reset the active session |
| POST | `/api/engagement/score` | Score a fused session |
| WS | `/ws/audio` | Receive 16-bit PCM audio bytes and return metrics |
| WS | `/ws/vision` | Send camera frames and receive detections |

## Offline operation

No API key is needed. Webcam frames, microphone samples, attendance records, and engagement calculations stay within the local application.

## Deploy to Render

The repository includes a Render Blueprint in `render.yaml`.

1. Push the project to GitHub.
2. In Render, choose **New → Blueprint** and connect the repository.
3. Review both services: `classroom-intelligence-api` and `classroom-intelligence-web`.
4. Apply the blueprint, then wait for both deployments to finish.
5. Open the generated frontend URL and allow camera and microphone permissions.

The blueprint connects the frontend to the backend automatically. Do not commit secrets: this project does not need API keys for local operation.

### Important camera requirements

Browser camera and microphone access requires HTTPS. Render supplies HTTPS automatically. A permission prompt is expected on the first visit.

## Troubleshooting

- **Frontend says API offline:** start uvicorn on port 8000 and verify `/api/health`.
- **Camera or microphone denied:** allow permissions in the browser site settings, then reload.
- **localhost connection refused:** use `localhost`, not a network IP, unless both servers and CORS origins are configured for that address.
- **OpenCV cannot find the camera:** ensure another application is not exclusively using it and select the correct device in Windows privacy settings.
- **Audio analysis has no data:** browsers require HTTPS or `localhost` for microphone access. Use the provided localhost URL.

## Project structure

```text
backend/       FastAPI, WebSockets, vision, audio, fusion, and scoring
frontend/     React and Vite dashboard
```
