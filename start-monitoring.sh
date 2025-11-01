#!/bin/bash

echo "🚀 Starting Email Responder with Monitoring Stack..."

# Create data directory
mkdir -p data

# Start all services
docker-compose up -d

echo "✅ Services started!"
echo ""
echo "📊 Access your services:"
echo "   FastAPI:    http://localhost:8000"
echo "   Prometheus: http://localhost:9090"
echo "   Grafana:    http://localhost:3000 (admin/admin)"
echo ""
echo "📈 Grafana Dashboard will be auto-imported"
echo "🔍 Check logs: docker-compose logs -f"
echo "🛑 Stop all:   docker-compose down"
