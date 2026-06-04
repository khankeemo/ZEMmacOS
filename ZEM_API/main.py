"""
ZEM License API — Cloud-authoritative licensing server.

Run: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from routes import admin_routes, auth_routes, license_routes, trial_routes
from security.rate_limit import limiter
from services.startup_service import run_startup

load_dotenv()

app = FastAPI(
    title="ZEMmacOS License API",
    description="Professional cloud-first license system",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(license_routes.router)
app.include_router(trial_routes.router)
app.include_router(admin_routes.router)


@app.on_event("startup")
def on_startup():
    run_startup()


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
