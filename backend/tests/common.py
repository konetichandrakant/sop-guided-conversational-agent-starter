"""Shared helpers for the agent tests: env bootstrap, turn runner and the DeepEval judge."""

import json
import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(BACKEND_DIR / ".env")

HAS_MODEL_KEY = (
    bool(os.environ.get("MODEL_API_TOKEN"))
    and os.environ["MODEL_API_TOKEN"] not in ("", "your-api-key-here")
)

from agent.agent import run_turn  # noqa: E402


def new_session() -> str:
    return uuid4().hex


def turn(session_id: str, prompt: str) -> dict:
    return run_turn(session_id, prompt)


# judge that reuses the agent's own provider and token, so no separate judge key is needed
from deepeval.metrics import GEval  # noqa: E402
from deepeval.models import DeepEvalBaseLLM  # noqa: E402
from deepeval.test_case import SingleTurnParams  # noqa: E402


class AgentProviderJudge(DeepEvalBaseLLM):
    def __init__(self):
        from agent.agent import _build_model

        self.model = _build_model()

    def load_model(self):
        return self.model

    def get_model_name(self):
        return os.environ.get("MODEL_NAME", "judge")

    def generate(self, prompt, schema=None, **kwargs):
        text = self.model.invoke(prompt).content
        if schema is None:
            return text
        return self._parse(text, schema)

    async def a_generate(self, prompt, schema=None, **kwargs):
        import asyncio

        return await asyncio.to_thread(self.generate, prompt, schema)

    @staticmethod
    def _parse(text, schema):
        cleaned = re.sub(r"```(?:json)?|```", "", str(text)).strip()
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            try:
                return schema(**json.loads(cleaned[start : end + 1]))
            except Exception:
                pass
        return schema.model_validate_json(cleaned)


@lru_cache(maxsize=1)
def judge() -> AgentProviderJudge:
    return AgentProviderJudge()


def judge_eval(name: str, criteria: str, threshold: float = 0.6, with_expected: bool = False) -> GEval:
    params = [SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT]
    if with_expected:
        params.append(SingleTurnParams.EXPECTED_OUTPUT)
    return GEval(
        name=name,
        criteria=criteria,
        evaluation_params=params,
        threshold=threshold,
        model=judge(),
        async_mode=False,
        strict_mode=False,
        verbose_mode=False,
    )
