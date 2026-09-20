import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import db
from backend.routes.assessments import router
from backend.routes.demo_auth import router as demo_auth_router

# Local dev defaults (Vite's default port, both hostname forms). Set
# BACKEND_CORS_ORIGINS (comma-separated) to the real deployed frontend
# origin(s) in production -- never widen this back to "*".
_DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(lifespan=lifespan)

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
app.include_router(demo_auth_router)
