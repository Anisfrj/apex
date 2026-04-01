#!/bin/bash
# Trigger all sync tasks manually (useful for first run)
API_URL="${1:-http://localhost:8000}"

echo "=== APEX Screener — Trigger All Syncs ==="
echo "API: $API_URL"
echo ""

# Check backend is reachable
echo "Checking backend..."
if ! curl -sf "$API_URL/api/health" > /dev/null 2>&1; then
    echo "⚠ Backend is not reachable at $API_URL"
    echo "  Make sure services are running: docker compose up -d"
    echo "  Check logs: docker compose logs backend"
    exit 1
fi
echo "Backend is healthy."
echo ""

trigger() {
    local name=$1
    local endpoint=$2
    echo "→ $name..."
    RESPONSE=$(curl -sf -X POST "$API_URL/api/trigger/$endpoint" 2>&1)
    if [ $? -eq 0 ]; then
        echo "  $RESPONSE"
    else
        echo "  ⚠ Failed: $RESPONSE"
    fi
}

trigger "1/6 Syncing macro data (FRED)" "sync-macro"
trigger "2/6 Syncing sector data (FMP)" "sync-sectors"
trigger "3/6 Syncing crypto data (DeFiLlama)" "sync-crypto"
trigger "4/6 Scanning insider filings (SEC EDGAR)" "scan-insiders"
trigger "5/6 Processing equity alerts" "process-equity-alerts"
trigger "6/6 Processing crypto alerts" "process-crypto-alerts"

echo ""
echo "=== All tasks queued! Check Celery worker logs: ==="
echo "  docker compose logs -f celery-worker"
