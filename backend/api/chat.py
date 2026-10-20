from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from schema.chat import ChatRequest, ChatResponse
from services.chat import get_response_from_chatbot

app = FastAPI()

# The test UI runs on a different origin than the API; open for the local demo.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/chat")
def call_chatbot(request: ChatRequest) -> ChatResponse:
    return get_response_from_chatbot(request)
