#!/bin/bash
# IDF Application Stop Script

echo "🛑 Stopping IDF Application..."

# Stop all containers
docker-compose down

echo "✅ IDF Application stopped successfully!"