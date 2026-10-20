from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(description="One user message for the SOP-guided claims agent", min_length=1)
    session_id: str = Field(
        default="default",
        description="Conversation session id; the agent keeps context across messages of the same session",
    )


class ChatResponse(BaseModel):
    response: str = Field(description="The agent's answer to the user message")
    phase: str = Field(description="Current SOP phase: VERIFY_ID, RESOLVE_INTENT, PROCESS_CASE or POST_PROCESS")
