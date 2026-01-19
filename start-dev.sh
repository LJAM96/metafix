#!/bin/bash
set -e

echo "Starting MetaFix in development mode..."

# Install frontend dependencies if needed
cd /app/frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start backend with hot reload
cd /app/backend
echo "Starting backend on port 8000 with hot reload..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend dev server
cd /app/frontend
echo "Starting frontend on port 3000 with hot reload..."
npm run dev &
FRONTEND_PID=$!

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" SIGTERM SIGINT

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
