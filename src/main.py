"""
SkillBridge Attendance Management API
FastAPI application entry point.

Run locally:
    uvicorn src.main:app --reload
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.db.database import Base, engine
import src.models  # noqa: F401 – ensures all models are registered before create_all
from src.routers.auth import router as auth_router
from src.routers.batches import router as batches_router
from src.routers.sessions import router as sessions_router
from src.routers.attendance import router as attendance_router
from src.routers.institutions import router as institutions_router
from src.routers.programme import programme_router, monitoring_router

# Create all tables on startup (idempotent)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SkillBridge Attendance API",
    description="Role-based attendance management for a fictional state-level skilling programme.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(batches_router)
app.include_router(sessions_router)
app.include_router(attendance_router)
app.include_router(institutions_router)
app.include_router(programme_router)
app.include_router(monitoring_router)


# ── Global exception handler: convert unhandled ValueError → 422 ──────────────
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "SkillBridge Attendance API"}
