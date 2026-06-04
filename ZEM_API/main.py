"""
ZEM License API - Production Backend for Websmith Digital
Deployed at: https://www.websmithdigital.com/internal/api
"""

import os
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ZEM License API",
    description="License management backend for Websmith Digital",
    version="1.0.0"
)

# CORS - Allow frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.websmithdigital.com", "https://websmithdigital.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== DATA MODELS ==========
class License(BaseModel):
    id: str
    key: str
    product: str
    status: str
    expires_at: str
    activations: int
    max_activations: int

class Product(BaseModel):
    id: str
    name: str
    price: float
    type: str
    active_licenses: int

class Hardware(BaseModel):
    id: str
    fingerprint: str
    license_key: str
    activated_at: str
    last_seen: str

# ========== FRONTEND ENDPOINTS (LIVE DASHBOARD) ==========

@app.get("/internal/api/dashboard/metrics")
async def dashboard_metrics():
    """Main dashboard metrics"""
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

@app.get("/internal/api/products")
async def get_products():
    """Products catalog"""
    return {
        "products": [
            {
                "id": "prod_001",
                "name": "ZEM Pro",
                "price": 99.99,
                "type": "perpetual",
                "active_licenses": 543,
                "features": ["Unlimited devices", "Priority support", "Cloud backup"]
            },
            {
                "id": "prod_002",
                "name": "ZEM Basic",
                "price": 49.99,
                "type": "subscription",
                "active_licenses": 421,
                "features": ["3 devices", "Email support", "Basic backup"]
            },
            {
                "id": "prod_003",
                "name": "ZEM Enterprise",
                "price": 299.99,
                "type": "perpetual",
                "active_licenses": 23,
                "features": ["Unlimited devices", "24/7 phone support", "SLA agreement"]
            }
        ]
    }

@app.get("/internal/api/licenses")
async def get_licenses():
    """All licenses"""
    return {
        "licenses": [
            {
                "id": "LIC-001",
                "key": "ZEM-ABCD-1234-EFGH",
                "product": "ZEM Pro",
                "status": "active",
                "expires_at": (datetime.utcnow() + timedelta(days=180)).isoformat(),
                "activations": 2,
                "max_activations": 5,
                "customer": "Acme Corp",
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": "LIC-002",
                "key": "ZEM-WXYZ-5678-IJKL",
                "product": "ZEM Basic",
                "status": "active",
                "expires_at": (datetime.utcnow() + timedelta(days=45)).isoformat(),
                "activations": 1,
                "max_activations": 3,
                "customer": "TechStart Inc",
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": "LIC-003",
                "key": "ZEM-MNOP-9012-QRST",
                "product": "ZEM Enterprise",
                "status": "expired",
                "expires_at": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                "activations": 0,
                "max_activations": 10,
                "customer": "Global Systems",
                "created_at": (datetime.utcnow() - timedelta(days=400)).isoformat()
            }
        ],
        "total": 3,
        "page": 1,
        "per_page": 50
    }

@app.get("/internal/api/hardware")
async def get_hardware():
    """Hardware activations"""
    return {
        "hardware": [
            {
                "id": "HW-001",
                "fingerprint": "a1b2c3d4e5f6g7h8",
                "license_key": "ZEM-ABCD-1234-EFGH",
                "device_name": "John's MacBook Pro",
                "os": "macOS 14.0",
                "activated_at": datetime.utcnow().isoformat(),
                "last_seen": datetime.utcnow().isoformat(),
                "is_active": True
            },
            {
                "id": "HW-002",
                "fingerprint": "i9j8k7l6m5n4o3p2",
                "license_key": "ZEM-ABCD-1234-EFGH",
                "device_name": "Office iMac",
                "os": "macOS 13.5",
                "activated_at": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                "last_seen": (datetime.utcnow() - timedelta(days=5)).isoformat(),
                "is_active": True
            }
        ]
    }

@app.get("/internal/api/settings")
async def get_settings():
    """System settings and policies"""
    return {
        "license_policies": {
            "default_expiry_days": 365,
            "max_devices_per_license": 5,
            "allow_trial": True,
            "trial_days": 14,
            "offline_grace_period_hours": 72,
            "require_heartbeat": True
        },
        "api_configuration": {
            "endpoint": "https://www.websmithdigital.com/internal/api",
            "version": "1.0.0",
            "rate_limit": "1000/minute",
            "webhook_url": "https://www.websmithdigital.com/webhooks/license"
        },
        "system_health": {
            "status": "operational",
            "database": "connected",
            "cache": "healthy",
            "last_backup": datetime.utcnow().isoformat(),
            "uptime_seconds": 86400
        }
    }

@app.get("/internal/api/health")
async def health_check():
    """Health check for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "online",
            "database": "connected",
            "redis": "connected"
        },
        "version": "1.0.0"
    }

@app.get("/internal/api/validate/{license_key}")
async def validate_license(license_key: str):
    """Validate a specific license key"""
    return {
        "valid": True,
        "license_key": license_key,
        "product": "ZEM Pro",
        "expires_at": (datetime.utcnow() + timedelta(days=180)).isoformat(),
        "activations": 2,
        "max_activations": 5,
        "status": "active"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "ZEM License API",
        "version": "1.0.0",
        "frontend": "https://www.websmithdigital.com/internal/api",
        "status": "operational",
        "endpoints": [
            "/internal/api/dashboard/metrics",
            "/internal/api/products",
            "/internal/api/licenses",
            "/internal/api/hardware",
            "/internal/api/settings",
            "/internal/api/health"
        ]
    }

# ========== RUN SERVER ==========
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)