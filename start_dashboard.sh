#!/bin/bash

# IDF Hebrew Dashboard Startup Script
# This script starts the Hebrew RTL dashboard with 4 pie charts

echo "🚀 Starting IDF Hebrew Dashboard with 4 Pie Charts"
echo "============================================"

# Set environment variables
export NODE_ENV=development
export VITE_API_BASE_URL=http://localhost:8000/api/v1
export VITE_DB_RECORDS_COUNT=494
export VITE_DEFAULT_LANGUAGE=he
export VITE_RTL_ENABLED=true
export VITE_REALTIME_ENABLED=true
export VITE_REALTIME_INTERVAL=30000

# Check if we're in the correct directory
if [ ! -f "frontend/package.json" ]; then
    echo "❌ Error: Please run this script from the IDF project root directory"
    exit 1
fi

# Navigate to frontend directory
cd frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "🔧 Creating environment file..."
    cp .env.example .env
fi

# Start the development server
echo "🌐 Starting Hebrew RTL Dashboard..."
echo "📊 Features:"
echo "   - 4 Pie Charts: Building, General, Engineering, Operational Readiness"
echo "   - Hebrew RTL Support"
echo "   - Real-time Updates (30s interval)"
echo "   - PostgreSQL Integration (494 records)"
echo "   - Building-Floor Hierarchy"
echo ""
echo "🔗 Dashboard will be available at: http://localhost:5173"
echo "💡 Press Ctrl+C to stop the server"
echo ""

# Run the development server
npm run dev

echo "✅ Dashboard server stopped"