#!/bin/bash
set -e

echo "=== APEX Screener — Database Initialization ==="
echo ""

# 1. Wait for PostgreSQL to be ready
echo "1/3 — Waiting for PostgreSQL..."
until docker compose exec db pg_isready -U ${POSTGRES_USER:-apex} > /dev/null 2>&1; do
    echo "  PostgreSQL not ready, waiting 2s..."
    sleep 2
done
echo "  PostgreSQL is ready."
echo ""

# 2. Create TimescaleDB extension
echo "2/3 — Creating TimescaleDB extension..."
docker compose exec db psql -U ${POSTGRES_USER:-apex} -d ${POSTGRES_DB:-apex_screener} -c \
    "CREATE EXTENSION IF NOT EXISTS timescaledb;" 2>/dev/null || echo "  (TimescaleDB extension may already exist or not be available — continuing)"
echo ""

# 3. Wait for backend to be running, then create tables
echo "3/3 — Waiting for backend to start..."
MAX_WAIT=30
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if docker compose exec backend curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "  Backend is running."
        break
    fi
    echo "  Backend not ready, waiting 3s... ($WAITED/$MAX_WAIT)"
    WAITED=$((WAITED + 3))
    sleep 3
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo ""
    echo "⚠ Backend did not start in time. Check logs with:"
    echo "  docker compose logs backend"
    echo ""
    echo "Common issues:"
    echo "  - Missing .env file (copy from .env.example)"
    echo "  - DATABASE_URL incorrect in .env"
    echo "  - Python import errors"
    exit 1
fi

echo ""
echo "=== Database initialization complete! ==="
echo ""
echo "Tables are auto-created on backend startup."
echo "Run ./scripts/trigger-all.sh to load initial data."
