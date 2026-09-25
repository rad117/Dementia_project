# Backend service image. Build context is the repo root because
# backend/requirements.txt pulls in ../ml/requirements.txt, and the app
# imports ml.* and reads models/baseline_v2/* in-process.
FROM python:3.12-slim

# ffmpeg: required by faster-whisper/av for audio decoding.
# libsndfile1: required by soundfile/librosa.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
COPY ml/requirements.txt ml/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY ml ml
COPY models models

EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
