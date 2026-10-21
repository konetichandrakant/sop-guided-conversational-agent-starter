import json
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

from agent.tools import TOOLS

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

with open(Path(__file__).resolve().parent / "prompts.json", "r", encoding="utf-8") as file:
    prompts = json.load(file)


class AgentReply(BaseModel):
    answer: str = Field(description="The reply shown to the user")
    phase: Literal["VERIFY_ID", "RESOLVE_INTENT", "PROCESS_CASE", "POST_PROCESS"] = Field(
        description="SOP phase the conversation is in after this reply"
    )


_sessions: dict[str, list[dict]] = {}
MAX_HISTORY = 40
_agent = None


def _build_model():
    name = os.environ["MODEL_NAME"]

    if name.startswith("openrouter:"):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=name.split(":", 1)[1],
            api_key=os.environ["MODEL_API_TOKEN"],
            base_url=os.environ.get("OPENROUTER_BASE_URL"),
            max_tokens=int(os.environ.get("MODEL_MAX_TOKENS", "1024")),
        )

    return init_chat_model(name, api_key=os.environ["MODEL_API_TOKEN"])


def _get_agent():
    global _agent
    if _agent is None:
        _agent = create_agent(
            _build_model(),
            TOOLS,
            system_prompt=prompts["SYSTEM_PROMPT"],
            response_format=AgentReply,
        )
    return _agent


def run_turn(session_id: str, prompt: str) -> dict:
    history = _sessions.setdefault(session_id, [])
    history.append({"role": "user", "content": prompt})

    result = _get_agent().invoke({"messages": history[-MAX_HISTORY:]})
    reply: AgentReply = result["structured_response"]
    tools = [
        call["name"]
        for message in result["messages"]
        for call in (getattr(message, "tool_calls", None) or [])
    ]

    history.append({"role": "assistant", "content": reply.answer})
    return {"answer": reply.answer, "phase": reply.phase, "tools": tools}


def call_agent(session_id: str, prompt: str) -> tuple[str, str]:
    turn = run_turn(session_id, prompt)
    return turn["answer"], turn["phase"]
