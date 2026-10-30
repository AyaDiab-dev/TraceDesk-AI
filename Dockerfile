FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY agent/ ./agent/
COPY services/ ./services/
COPY dataset/ ./dataset/
COPY data/embeddings_cache.json ./data/embeddings_cache.json

EXPOSE 8000

CMD ["uvicorn", "services.resolveai_api:app", "--host", "0.0.0.0", "--port", "8000"]