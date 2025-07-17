#!/bin/bash
# IDF Application Development Startup Script

set -e

echo "🚀 Starting IDF Application Development Environment..."

# Load environment variables
if [ -f .env.development ]; then
    echo "📋 Loading development environment variables..."
    set -a && source .env.development && set +a
fi

# Create required directories
echo "📁 Creating required directories..."
mkdir -p backend/logs backend/uploads backend/temp
mkdir -p frontend/build
mkdir -p monitoring/data

# Start services
echo "🐳 Starting Docker containers..."
docker-compose up -d postgres redis

# Wait for database to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
until docker-compose exec postgres pg_isready -U idf_user -d idf_testing; do
    sleep 2
done

echo "⏳ Waiting for Redis to be ready..."
until docker-compose exec redis redis-cli ping; do
    sleep 2
done

# Start application services
echo "🔧 Starting application services..."
docker-compose up -d backend frontend

echo "✅ IDF Application is starting up!"
echo "📊 Backend API: http://localhost:8000"
echo "🌐 Frontend App: http://localhost:3000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "🔍 Logs: docker-compose logs -f"

# Optional: Open browser
if command -v xdg-open > /dev/null; then
    echo "🌐 Opening application in browser..."
    xdg-open http://localhost:3000
fi

echo "🎯 Development environment ready!"