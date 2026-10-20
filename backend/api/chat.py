from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from schema.chat import ChatRequest, ChatResponse
from services.chat import get_response_from_chatbot

app = FastAPI()

# The test UI runs on a different origin than the API; open for the local demo.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/chat")
def call_chatbot(request: ChatRequest) -> ChatResponse:
    return get_response_from_chatbot(request)


# Serve the test UI from the API itself (one origin, one container).
# Repo layout puts frontend/ next to backend/; the Docker image puts it at /app/frontend.
def _frontend_dir() -> Path | None:
    candidates = [
        Path(__file__).resolve().parents[2] / "frontend",  # repo layout
        Path(__file__).resolve().parents[1] / "frontend",  # docker layout
    ]
    return next((path for path in candidates if (path / "index.html").is_file()), None)


_frontend = _frontend_dir()
if _frontend is not None:
    # Mounted last so /chat and the OpenAPI routes keep priority over static files.
    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")
