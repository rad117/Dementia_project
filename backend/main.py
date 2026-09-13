from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.assessments import router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    # DEV ONLY — Phase 0. Replace with an explicit frontend origin allow-list
    # before any non-local deployment. See docs/ACTION_PLAN.md Phase 1.
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
