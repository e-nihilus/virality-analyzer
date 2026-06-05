#!/bin/bash
echo "Starting Aurea Viral Intelligence..."
echo ""
echo "[Backend]  http://127.0.0.1:8000/docs"
echo "[Frontend] http://localhost:5173"
echo ""

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "[venv] Activated .venv"
else
    echo "[venv] No .venv found — using system Python"
fi

# Start backend in background
python -m uvicorn app.main:app --reload --app-dir backend &
BACK_PID=$!

# Wait for backend to be ready
sleep 3

# Start frontend in background
(cd frontend && npm run dev) &
FRONT_PID=$!

# Trap Ctrl+C to kill both
trap "kill $BACK_PID $FRONT_PID 2>/dev/null; exit" INT TERM
wait
