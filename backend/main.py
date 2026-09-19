from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import db
from backend.routes.assessments import router
from backend.routes.demo_auth import router as demo_auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # DEV ONLY — Phase 0. Replace with an explicit frontend origin allow-list
    # before any non-local deployment. See docs/ACTION_PLAN.md Phase 1.
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(demo_auth_router)
