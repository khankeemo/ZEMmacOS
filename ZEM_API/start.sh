#!/bin/bash
# Startup script for Render deployment

echo "🚀 Starting ZEM License API on Render..."

# Set production environment
export USE_SQLITE_DEV=0
export PYTHONPATH=/app

# Run database migrations (creates tables)
python -c "from database import init_db; init_db(); print('✅ Database tables ready')"

# Start FastAPI with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000