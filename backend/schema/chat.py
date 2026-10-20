from pydantic import BaseModel, Field

class ChatRequest:
    prompt: str

class ChatResponse(BaseModel):
    response: str = Field(description="AI response if agent is clear and able to figure out and confident on answering user query.")
    follow_up: str = Field(description="AI response if agent is not clear and not able to figure out and not confident on answering user query.")