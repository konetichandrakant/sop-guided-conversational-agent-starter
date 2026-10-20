import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from agent.tools import get_claim, verify_profile

# MODEL_NAME / MODEL_API_TOKEN come from backend/.env
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

TOOLS = [verify_profile, get_claim]

with open(Path(__file__).resolve().parent / "prompts.json", "r", encoding="utf-8") as file:
    prompts = json.load(file)

_agent = None


def _get_agent():
    """Build the agent once: model from .env, SOP system prompt, the claims tools."""
    global _agent
    if _agent is None:
        model = init_chat_model(
            os.environ["MODEL_NAME"],  # provider-prefixed, e.g. "openai:gpt-4o-mini"
            api_key=os.environ["MODEL_API_TOKEN"],
        )
        _agent = create_agent(model, TOOLS, system_prompt=prompts["SYSTEM_PROMPT"])
    return _agent


def call_agent(prompt: str) -> str:
    """Run one user turn through the SOP-guided claims agent and return its answer."""
    result = _get_agent().invoke({"messages": [{"role": "user", "content": prompt}]})
    return result["messages"][-1].content
