# Builds the SOP claims agent: FastAPI backend + static test UI in one container.
# The API auth token is passed at runtime (docker compose env_file) - never baked in.
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY frontend/ ./frontend/

EXPOSE 8000

CMD ["uvicorn", "api.chat:app", "--host", "0.0.0.0", "--port", "8000"]
