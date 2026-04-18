#!/bin/bash
# RoboSpread launcher — starts backend + frontend

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Starting RoboSpread..."

# Start backend
echo "Starting backend..."
cd "$DIR/backend"
source venv/bin/activate
python main.py &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend..."
cd "$DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend running on http://localhost:8000"
echo "Frontend running on http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both."

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
