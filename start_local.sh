#!/bin/bash
# Local development startup script for KindRoot

set -e  # Exit on error

echo "🚀 Starting KindRoot Local Development Environment"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if ports are already in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  Port $1 is already in use. Killing process..."
        lsof -ti:$1 | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

echo "📋 Checking ports..."
check_port 8000
check_port 3000
check_port 3001

# Start backend
echo ""
echo -e "${BLUE}Starting Backend API (port 8000)...${NC}"
cd backend
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000 > /tmp/kindroot_backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 2

# Start admin frontend
echo -e "${BLUE}Starting Admin Frontend (port 3000)...${NC}"
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi
npm run dev > /tmp/kindroot_frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Start consumer frontend
echo -e "${BLUE}Starting Consumer Frontend (port 3001)...${NC}"
cd consumer_frontend
if [ ! -d "node_modules" ]; then
    echo "Installing consumer frontend dependencies..."
    npm install
fi
npm run dev > /tmp/kindroot_consumer.log 2>&1 &
CONSUMER_PID=$!
cd ..

# Wait for servers to be ready
sleep 3

echo ""
echo -e "${GREEN}✅ All servers started successfully!${NC}"
echo ""
echo "📍 Access your applications at:"
echo "   🔧 Backend API:       http://localhost:8000"
echo "   🏥 Admin Frontend:    http://localhost:3000"
echo "   🌐 Consumer Frontend: http://localhost:3001"
echo ""
echo "📝 Logs are available at:"
echo "   Backend:  tail -f /tmp/kindroot_backend.log"
echo "   Frontend: tail -f /tmp/kindroot_frontend.log"
echo "   Consumer: tail -f /tmp/kindroot_consumer.log"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Keep script running
wait
