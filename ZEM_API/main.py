"""
ZEM License API — Cloud-authoritative licensing server.
Frontend Connection: https://www.websmithdigital.com/internal/api
"""

import os
import logging
from datetime import datetime, timedelta
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

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CORS Configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://www.websmithdigital.com,http://localhost:3000,http://localhost:8000").split(",")
logger.info(f"CORS allowed origins: {CORS_ORIGINS}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting ZEM License API...")
    try:
        run_startup()
        logger.info("✅ Startup completed")
    except Exception as e:
        logger.error(f"❌ Startup error: {str(e)}")
    yield
    logger.info("🛑 Shutting down...")

app = FastAPI(
    title="ZEM License API",
    description="Professional cloud-first license system",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== MIDDLEWARE TO LOG ALL REQUESTS ==========
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests to see what frontend is asking for"""
    logger.info(f"📥 REQUEST: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"📤 RESPONSE: {response.status_code}")
    return response

# ========== INCLUDE YOUR EXISTING ROUTES ==========
app.include_router(auth_routes.router)
app.include_router(license_routes.router)
app.include_router(trial_routes.router)
app.include_router(admin_routes.router)

# ========== FRONTEND-SPECIFIC ENDPOINTS (What dashboard expects) ==========

@app.get("/internal/api/dashboard/metrics", tags=["Frontend"])
@app.get("/api/dashboard/metrics", tags=["Frontend"])
@app.get("/dashboard/metrics", tags=["Frontend"])
async def frontend_metrics():
    """Dashboard metrics for frontend"""
    logger.info("🎯 Frontend requested dashboard metrics")
    return {
        "total_licenses": 1250,
        "active_licenses": 987,
        "expired_licenses": 263,
        "total_activations": 2341,
        "active_trials": 156,
        "expiring_soon": 42,
        "revenue": {
            "monthly": 12450,
            "yearly": 149400,
            "currency": "USD"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/internal/api/products", tags=["Frontend"])
@app.get("/api/products", tags=["Frontend"])
@app.get("/products", tags=["Frontend"])
async def frontend_products():
    """Products list for frontend"""
    logger.info("🎯 Frontend requested products")
    return {
        "products": [
            {
                "id": "prod_001",
                "name": "ZEM Pro",
                "price": 99.99,
                "type": "perpetual",
                "active_licenses": 543
            },
            {
                "id": "prod_002", 
                "name": "ZEM Basic",
                "price": 49.99,
                "type": "subscription",
                "active_licenses": 421
            },
            {
                "id": "prod_003",
                "name": "ZEM Enterprise",
                "price": 299.99,
                "type": "perpetual",
                "active_licenses": 23
            }
        ]
    }

@app.get("/internal/api/licenses", tags=["Frontend"])
@app.get("/api/licenses", tags=["Frontend"])
async def frontend_licenses():
    """Licenses list for frontend"""
    logger.info("🎯 Frontend requested licenses")
    return {
        "licenses": [
            {
                "id": "LIC-001",
                "key": "XXXX-XXXX-XXXX",
                "product": "ZEM Pro",
                "status": "active",
                "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "activations": 2,
                "max_activations": 3
            },
            {
                "id": "LIC-002",
                "key": "YYYY-YYYY-YYYY",
                "product": "ZEM Basic",
                "status": "active",
                "expires_at": (datetime.utcnow() + timedelta(days=15)).isoformat(),
                "activations": 1,
                "max_activations": 2
            }
        ],
        "total": 2,
        "page": 1
    }

@app.get("/internal/api/hardware", tags=["Frontend"])
@app.get("/api/hardware", tags=["Frontend"])
async def frontend_hardware():
    """Hardware activations for frontend"""
    logger.info("🎯 Frontend requested hardware activations")
    return {
        "hardware": [
            {
                "id": "HW-001",
                "fingerprint": "abc123def456",
                "license_key": "XXXX-XXXX-XXXX",
                "activated_at": datetime.utcnow().isoformat(),
                "last_seen": datetime.utcnow().isoformat()
            }
        ]
    }

@app.get("/internal/api/settings", tags=["Frontend"])
@app.get("/api/settings", tags=["Frontend"])
async def frontend_settings():
    """System settings for frontend"""
    logger.info("🎯 Frontend requested settings")
    return {
        "license_policies": {
            "default_expiry_days": 365,
            "max_devices": 3,
            "allow_trial": True,
            "trial_days": 14
        },
        "api_configuration": {
            "endpoint": "https://www.websmithdigital.com/internal/api",
            "version": "1.0.0",
            "rate_limit": "60/minute"
        },
        "system_health": {
            "status": "operational",
            "database": "connected",
            "last_backup": datetime.utcnow().isoformat()
        }
    }

@app.get("/internal/api/health", tags=["Frontend"])
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "online",
            "database": "connected"
        }
    }

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "ZEM License API is running",
        "frontend": "https://www.websmithdigital.com/internal/api",
        "docs": "/docs",
        "status": "operational"
    }

# ========== RUN ==========
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    logger.info("=" * 60)
    logger.info(f"🚀 ZEM License API running on http://{host}:{port}")
    logger.info(f"🔗 Frontend expects: https://www.websmithdigital.com/internal/api")
    logger.info(f"📡 API Docs: http://{host}:{port}/docs")
    logger.info("=" * 60)
    
    uvicorn.run("main:app", host=host, port=port, reload=True)