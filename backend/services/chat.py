from agent.agent import call_agent
from schema.chat import ChatRequest, ChatResponse


def get_response_from_chatbot(request: ChatRequest) -> ChatResponse:
    """API entry: pass the user's message to the session-aware agent, return answer + phase."""
    answer, phase = call_agent(request.session_id, request.prompt)
    return ChatResponse(response=answer, phase=phase)
