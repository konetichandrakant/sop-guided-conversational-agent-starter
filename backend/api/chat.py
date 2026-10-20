from fastapi import FastAPI

from schema.chat import ChatRequest, ChatResponse
from services.chat import get_response_from_chatbot

app = FastAPI()


@app.post("/chat")
def call_chatbot(request: ChatRequest) -> ChatResponse:
    return get_response_from_chatbot(request.prompt)
