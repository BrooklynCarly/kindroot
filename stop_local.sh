#!/bin/bash
# Stop all local development servers

echo "🛑 Stopping all KindRoot servers..."

# Kill processes on our ports
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✅ Backend stopped" || echo "ℹ️  Backend not running"
lsof -ti:3000 | xargs kill -9 2>/dev/null && echo "✅ Admin frontend stopped" || echo "ℹ️  Admin frontend not running"
lsof -ti:3001 | xargs kill -9 2>/dev/null && echo "✅ Consumer frontend stopped" || echo "ℹ️  Consumer frontend not running"

# Clean up log files
rm -f /tmp/kindroot_*.log 2>/dev/null && echo "✅ Logs cleaned" || true

echo ""
echo "✅ All servers stopped"
