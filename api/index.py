# Vercel serverless entry: exposes the FastAPI app that lives in backend/api/chat.py.
# Vercel routes any request rewritten to /api/index here and runs the ASGI app below.
import sys
from pathlib import Path

# The backend imports its modules as top-level packages (agent, schema, services),
# so the backend directory itself must be importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from api.chat import app  # noqa: E402
