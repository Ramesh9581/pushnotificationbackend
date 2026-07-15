"""
main.py
FastAPI application entry point.

Start with:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import ping_db
from models.orm_models import Base
from db.database import engine
from routes.devices       import router as devices_router
from routes.notifications import router as notifications_router
from routes.logs          import router as logs_router
from routes.users         import router as users_router
from services.firebase_service import init_firebase, is_firebase_ready
from models.schemas import HealthResponse

# ── Create tables (idempotent – only creates if not exists) ────────────────────
Base.metadata.create_all(bind=engine)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Push Notification Service",
    description=(
        "REST API for registering web device tokens and sending "
        "Firebase push notifications with screen-navigation support."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# In production replace "*" with your actual frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup ────────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    print("[App] Starting Push Notification Service …")
    db_ok = ping_db()
    print(f"[App] Database: {'✓ connected' if db_ok else '✗ unreachable'}")
    fb_ok = init_firebase()
    print(f"[App] Firebase: {'✓ ready' if fb_ok else '✗ not configured'}")

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(devices_router,       prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(logs_router,          prefix="/api/v1")
app.include_router(users_router,         prefix="/api/v1")

# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Quick liveness probe – checks DB connectivity and Firebase status."""
    db_ok = ping_db()
    return HealthResponse(
        status   = "ok" if db_ok else "degraded",
        database = "connected"     if db_ok                else "unreachable",
        firebase = "initialised"   if is_firebase_ready()  else "not configured",
    )

@app.get("/", tags=["Health"])
def root():
    return {
        "service": "Push Notification Service",
        "docs":    "/docs",
        "health":  "/health",
    }
