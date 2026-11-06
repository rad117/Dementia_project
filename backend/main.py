import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import db, seed
from backend.routes.assessments import router
from backend.routes.auth import router as auth_router
from ml.inference.predict import preload as preload_model
from backend.routes.monitoring import router as monitoring_router
from monitoring import store as monitoring_store

# Local dev defaults (Vite's default port, both hostname forms). Set
# BACKEND_CORS_ORIGINS (comma-separated) to the real deployed frontend
# origin(s) in production -- never widen this back to "*".
_DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    seed.run()
    preload_model()
    monitoring_store.init_db()
    yield


app = FastAPI(title="Memora API", lifespan=lifespan)

allow_origins = [
    origin.strip()
    for origin in os.environ.get("BACKEND_CORS_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(auth_router)
app.include_router(monitoring_router)


@app.get("/", include_in_schema=False)
def root() -> dict:
    """Landing response for anyone opening the API's base URL in a browser."""
    return {
        "service": "Memora API",
        "status": "ok",
        "description": "Speech-based cognitive screening and home safety monitoring.",
        "health": "/health",
        "docs": "/docs",
    }
