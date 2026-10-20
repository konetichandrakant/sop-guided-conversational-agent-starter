from agent.agent import call_agent
from schema.chat import ChatResponse


def get_response_from_chatbot(prompt: str) -> ChatResponse:
    """API entry: pass the user's message to the agent and wrap its answer."""
    return ChatResponse(response=call_agent(prompt))
