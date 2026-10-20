from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(description="One user message for the SOP-guided claims agent", min_length=1)


class ChatResponse(BaseModel):
    response: str = Field(description="The agent's answer to the user message")
