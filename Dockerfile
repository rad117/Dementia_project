# Backend service image. Build context is the repo root because
# backend/requirements.txt pulls in ../ml/requirements.txt, and the app
# imports ml.* and monitoring.* and reads models/baseline_v2/* in-process.
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
# Safety-monitoring rules engine + store (backend/main.py imports it at
# startup). Camera/VLM deps stay optional, so nothing extra to install.
COPY monitoring monitoring

# Pre-warm at build time (the free runtime CPU is too slow for this): numba JIT
# cache for librosa and the Whisper weights, so the first upload isn't a timeout.
ENV NUMBA_CACHE_DIR=/app/.numba
RUN python -c "import numpy as np; from ml.features.acoustic import extract_features; from faster_whisper import WhisperModel; t=np.arange(16000*6)/16000; import io,wave; b=io.BytesIO(); w=wave.open(b,'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes((6000*np.sin(2*np.pi*150*t)*(np.sin(2*np.pi*2*t)>0)).astype('int16').tobytes()); w.close(); extract_features(b.getvalue()); WhisperModel('tiny.en', device='cpu', compute_type='int8')" || true

# Memory-safe defaults for a 512 MB host; Render dashboard env vars override these.
ENV MAX_ANALYSIS_SECONDS=30 WHISPER_MODEL=tiny.en MODEL_DIR=models/baseline_v1

EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
