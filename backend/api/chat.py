from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from schema.chat import ChatRequest, ChatResponse
from services.chat import get_response_from_chatbot

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/chat")
def call_chatbot(request: ChatRequest) -> ChatResponse:
    return get_response_from_chatbot(request)


# serve the UI from the API itself; repo layout and docker layout differ
def _frontend_dir():
    candidates = [
        Path(__file__).resolve().parents[2] / "frontend",  # repo layout
        Path(__file__).resolve().parents[1] / "frontend",  # docker layout
    ]
    return next((path for path in candidates if (path / "index.html").is_file()), None)


_frontend = _frontend_dir()
if _frontend is not None:
    # mounted last so /chat and the docs routes keep priority
    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")
