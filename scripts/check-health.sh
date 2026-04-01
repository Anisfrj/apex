#!/bin/bash
echo "=== APEX Screener — Health Check ==="
echo ""

echo "── Docker Services ──"
docker compose ps
echo ""

echo "── Backend Logs (last 30 lines) ──"
docker compose logs --tail=30 backend 2>&1
echo ""

echo "── Celery Worker Logs (last 15 lines) ──"
docker compose logs --tail=15 celery-worker 2>&1
echo ""

echo "── API Health ──"
curl -s http://localhost:8000/api/health 2>&1 || echo "⚠ Backend not reachable on port 8000"
echo ""

echo "── System Status ──"
curl -s http://localhost:8000/api/status 2>&1 | python3 -m json.tool 2>/dev/null || echo "⚠ Could not fetch status"
echo ""
