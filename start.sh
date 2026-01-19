#!/bin/bash
set -e

echo "Starting MetaFix..."

# Start backend with uvicorn
cd /app/backend
echo "Starting backend on port 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend
cd /app/frontend
echo "Starting frontend on port 3000..."
npm run start &
FRONTEND_PID=$!

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" SIGTERM SIGINT

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
