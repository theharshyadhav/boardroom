#!/usr/bin/env bash
# Starts both the FastAPI backend and Next.js frontend with one command.
# macOS / Linux (or WSL/Git-Bash on Windows). Ctrl+C stops both cleanly.
set -e
cd "$(dirname "$0")"

if [ ! -d "backend/venv" ]; then
  echo "→ First run: creating backend virtualenv and installing dependencies..."
  python3 -m venv backend/venv
  ./backend/venv/bin/pip install --quiet -r backend/requirements.txt
fi

if [ ! -d "frontend/node_modules" ]; then
  echo "→ First run: installing frontend dependencies (npm install)..."
  (cd frontend && npm install)
fi

if [ ! -f "backend/.env" ]; then
  cp backend/.env.example backend/.env
  echo "→ Created backend/.env from the example — add an API key there for live LLM narration (optional)."
fi
if [ ! -f "frontend/.env.local" ]; then
  echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/.env.local
fi

cleanup() {
  echo ""
  echo "→ Stopping BoardMind..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM

echo "→ Starting backend on http://localhost:8000 ..."
(cd backend && ./venv/bin/uvicorn app.main:app --port 8000) &
BACKEND_PID=$!

echo "→ Starting frontend on http://localhost:3000 ..."
(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo ""
echo "  BoardMind is starting up:"
echo "    Frontend  → http://localhost:3000"
echo "    Backend   → http://localhost:8000  (docs at /docs)"
echo "  Press Ctrl+C to stop both."
echo ""

wait "$BACKEND_PID" "$FRONTEND_PID"
