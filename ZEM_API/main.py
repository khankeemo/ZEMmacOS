"""
ZEM License API — Cloud-authoritative licensing server.
Frontend Connection: https://www.websmithdigital.com/internal/api

Run: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from routes import admin_routes, auth_routes, license_routes, trial_routes
from security.rate_limit import limiter
from services.startup_service import run_startup

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CORS Configuration - Allow frontend domain
# Read from .env or default to websmithdigital.com
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://www.websmithdigital.com").split(",")
logger.info(f"CORS allowed origins: {CORS_ORIGINS}")

# Database and API Configuration
API_PREFIX = os.getenv("API_PREFIX", "/api")
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting ZEM License API...")
    logger.info(f"🔗 Frontend URL: https://www.websmithdigital.com/internal/api")
    logger.info(f"📡 API Docs available at: /docs")
    logger.info(f"🌐 CORS enabled for: {CORS_ORIGINS}")
    
    # Run existing startup service
    try:
        run_startup()
        logger.info("✅ Startup service completed")
    except Exception as e:
        logger.error(f"❌ Startup service failed: {str(e)}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down ZEM License API...")


# Initialize FastAPI
app = FastAPI(
    title="ZEM License API",
    description="Professional cloud-first license system for Websmith Digital",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Rate limiting setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# CORS Middleware (Critical for frontend connection)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)


# ========== INCLUDE ROUTES ==========
# Add API prefix to all routes for consistency
app.include_router(auth_routes.router, prefix=f"{API_PREFIX}/auth", tags=["Authentication"])
app.include_router(license_routes.router, prefix=f"{API_PREFIX}/licenses", tags=["Licenses"])
app.include_router(trial_routes.router, prefix=f"{API_PREFIX}/trial", tags=["Trial"])
app.include_router(admin_routes.router, prefix=f"{API_PREFIX}/admin", tags=["Admin"])

# Keep root routes without prefix for compatibility
app.include_router(auth_routes.router, tags=["Authentication (Legacy)"])
app.include_router(license_routes.router, tags=["Licenses (Legacy)"])
app.include_router(trial_routes.router, tags=["Trial (Legacy)"])
app.include_router(admin_routes.router, tags=["Admin (Legacy)"])


# ========== FRONTEND CONNECTION ENDPOINTS ==========

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API status"""
    return {
        "name": "ZEM License API",
        "version": "1.0.0",
        "status": "operational",
        "frontend_url": "https://www.websmithdigital.com/internal/api",
        "api_docs": "/docs",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for frontend monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime_seconds": get_uptime(),
        "services": {
            "api": "online",
            "database": check_database_connection(),
            "rate_limiter": "active"
        }
    }


@app.get("/api/health", tags=["Health"])
async def api_health():
    """Alias for health check - Frontend compatibility"""
    return await health_check()


@app.get("/api/system/status", tags=["System"])
async def system_status():
    """System status endpoint for dashboard"""
    return {
        "api_status": "online",
        "database_status": "connected" if check_database_connection() else "disconnected",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "cors_enabled": True,
        "allowed_origins": CORS_ORIGINS,
        "rate_limiting": {
            "enabled": True,
            "requests_per_minute": int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
        }
    }


@app.get("/api/dashboard/metrics", tags=["Dashboard"])
async def dashboard_metrics():
    """Main dashboard metrics for frontend"""
    # This will be connected to your actual metrics service
    # Placeholder until we integrate with your existing services
    return {
        "total_licenses": 0,
        "active_licenses": 0,
        "total_activations": 0,
        "active_trials": 0,
        "expiring_soon": 0,
        "revenue": {
            "monthly": 0,
            "yearly": 0
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.options("/{rest_of_path:path}")
async def preflight_handler():
    """Handle CORS preflight requests"""
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


# ========== ERROR HANDLERS ==========

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for better error responses"""
    logger.error(f"Global error: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if DEBUG_MODE else "An internal error occurred",
            "status": "error",
            "path": request.url.path
        }
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    """404 handler for undefined routes"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"Endpoint {request.url.path} not found",
            "status": "error",
            "path": request.url.path
        }
    )


# ========== HELPER FUNCTIONS ==========

def check_database_connection() -> bool:
    """Check if database is connected"""
    try:
        # Add your actual database check here
        # Example: from database.connection import get_db
        # with get_db() as db:
        #     db.execute("SELECT 1")
        return True  # Placeholder - update with actual DB check
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return False


def get_uptime() -> int:
    """Get server uptime in seconds"""
    # Placeholder - implement actual uptime tracking if needed
    import time
    if not hasattr(app, "_start_time"):
        app._start_time = time.time()
    return int(time.time() - app._start_time)


# ========== RUN CONFIGURATION ==========

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload_mode = os.getenv("RELOAD", "True").lower() == "true"
    
    logger.info("=" * 60)
    logger.info(f"🚀 Starting ZEM License API")
    logger.info(f"📁 Path: D:\ZEMmacOS\ZEM_API")
    logger.info(f"🌐 Host: {host}:{port}")
    logger.info(f"🔗 Frontend: https://www.websmithdigital.com/internal/api")
    logger.info(f"📚 API Docs: http://{host}:{port}/docs")
    logger.info(f"🔄 Reload mode: {reload_mode}")
    logger.info("=" * 60)
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload_mode,
        log_level="info"
    )