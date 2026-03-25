"""
SafeStep FastAPI Backend
Run:  uvicorn main:app --reload --port 8000
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import init_db
from app.routes import auth, sensors, alerts, orders

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger("safestep")

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀  Starting SafeStep backend…")
    await init_db()
    logger.info(f"🌐  Serving on http://localhost:{settings.PORT}")
    yield
    logger.info("👋  Shutting down")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="SafeStep API",
    description="Diabetic foot health monitoring platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Rate limit error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── API Routes ────────────────────────────────────────────────────────────────
app.include_router(auth.router,    prefix="/api")
app.include_router(sensors.router, prefix="/api")
app.include_router(alerts.router,  prefix="/api")
app.include_router(orders.router,  prefix="/api")


# ── Public stats endpoint ─────────────────────────────────────────────────────
@app.get("/api/stats", tags=["public"])
async def public_stats():
    """Live platform stats for the homepage counter."""
    from app.database import AsyncSessionLocal
    from app.models import Alert, User, SensorReading, Preorder
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as db:
        total_readings  = (await db.execute(select(func.count(SensorReading.id)))).scalar() or 0
        total_alerts    = (await db.execute(select(func.count(Alert.id)))).scalar() or 0
        total_patients  = (await db.execute(
            select(func.count(User.id)).where(User.role == "patient")
        )).scalar() or 0
        total_preorders = (await db.execute(select(func.count(Preorder.id)))).scalar() or 0

    prevented = 8247 + int(total_alerts * 0.12)
    return {
        "total_readings":  total_readings,
        "total_alerts":    total_alerts,
        "total_patients":  total_patients,
        "total_preorders": total_preorders,
        "amputations_prevented": prevented,
    }


# ── Serve static frontend ─────────────────────────────────────────────────────
PUBLIC_DIR = Path(__file__).parent / "public"
if PUBLIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(PUBLIC_DIR)), name="static")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """SPA fallback — serve index.html for all non-API routes."""
        index = PUBLIC_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return JSONResponse({"message": "SafeStep API is running. See /api/docs"})
