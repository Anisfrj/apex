#!/bin/bash
# APEX Equity Screener - Deployment Script
# Run this on your VPS: bash deploy_equity_screener.sh

set -e

echo "🚀 APEX Equity Screener Deployment"
echo "==================================="

# 1. Navigate to APEX directory
cd ~/apex || cd /root/apex || { echo "❌ apex directory not found"; exit 1; }

echo "📥 Step 1: Pulling latest code from GitHub..."
git pull origin main

echo "🗄️  Step 2: Creating equities_fundamentals table..."
docker exec -i apex-db psql -U apex -d apex_screener < scripts/create_equities_fundamentals_table.sql
echo "✅ Table created successfully"

echo "🔨 Step 3: Rebuilding backend with yfinance dependency..."
docker compose build backend

echo "♻️  Step 4: Restarting all services..."
docker compose down
docker compose up -d

echo "⏳ Step 5: Waiting for services to be healthy..."
sleep 10

echo "📊 Step 6: Checking container status..."
docker compose ps

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🧪 Test the equity screener:"
echo "   curl http://localhost:8000/api/trigger/sync-equities"
echo ""
echo "📈 View Swagger docs:"
echo "   http://51.255.200.29:8000/docs"
echo ""
echo "🌐 Frontend:"
echo "   http://51.255.200.29"
echo ""
echo "📝 Monitor logs:"
echo "   docker compose logs -f celery-worker"
