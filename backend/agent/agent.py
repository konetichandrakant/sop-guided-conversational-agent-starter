import json
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

from agent.tools import get_claim, verify_profile

# MODEL_NAME / MODEL_API_TOKEN come from backend/.env
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

TOOLS = [verify_profile, get_claim]

with open(Path(__file__).resolve().parent / "prompts.json", "r", encoding="utf-8") as file:
    prompts = json.load(file)


class AgentReply(BaseModel):
    """Structured final answer of every agent turn; drives the chat UI phase stepper."""

    answer: str = Field(description="The reply shown to the user")
    phase: Literal["VERIFY_ID", "RESOLVE_INTENT", "PROCESS_CASE", "POST_PROCESS"] = Field(
        description="SOP phase the conversation is in after this reply"
    )


# In-memory conversation store: session_id -> message history.
# Enough for a demo; swap for a redis/db-backed store in production.
_sessions: dict[str, list[dict]] = {}
MAX_HISTORY = 40

_agent = None


def _get_agent():
    """Build the agent once: model from .env, SOP system prompt, claims tools, structured replies."""
    global _agent
    if _agent is None:
        model = init_chat_model(
            os.environ["MODEL_NAME"],  # provider-prefixed, e.g. "openai:gpt-4o-mini"
            api_key=os.environ["MODEL_API_TOKEN"],
        )
        _agent = create_agent(
            model,
            TOOLS,
            system_prompt=prompts["SYSTEM_PROMPT"],
            response_format=AgentReply,
        )
    return _agent


def call_agent(session_id: str, prompt: str) -> tuple[str, str]:
    """Run one user turn inside a session; returns (answer, phase)."""
    history = _sessions.setdefault(session_id, [])
    history.append({"role": "user", "content": prompt})

    result = _get_agent().invoke({"messages": history[-MAX_HISTORY:]})
    reply: AgentReply = result["structured_response"]

    history.append({"role": "assistant", "content": reply.answer})
    return reply.answer, reply.phase
