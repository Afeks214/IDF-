#!/bin/bash
# IDF Application Restart Script

echo "🔄 Restarting IDF Application..."

# Stop all services
./stop.sh

# Start all services
./start.sh

echo "✅ IDF Application restarted successfully!"