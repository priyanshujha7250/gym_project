#!/usr/bin/env bash
# Startup script for FIT NATION Gym Platform

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo "   FIT NATION FITNESS & DIGITAL MANAGEMENT PLATFORM"
echo "=========================================================="

# Check Python 3
if command -v python3 >/dev/null 2>&1; then
    PY_BIN="python3"
elif [ -f "/opt/homebrew/bin/python3" ]; then
    PY_BIN="/opt/homebrew/bin/python3"
else
    echo "Error: Python 3 not found. Please install Python 3."
    exit 1
fi

export PYTHONPATH="$DIR/backend"

# Seed database if it doesn't exist
if [ ! -f "$DIR/backend/gym_platform.db" ]; then
    echo ">> First time setup: Initializing and seeding database..."
    $PY_BIN "$DIR/backend/seed_data.py"
fi

PORT="${PORT:-8000}"

echo ">> Starting FIT NATION server on http://localhost:$PORT ..."
echo ">> Public Website: http://localhost:$PORT/"
echo ">> Admin Portal:   http://localhost:$PORT/admin"
echo "   [Default Login: admin@gym.com / admin123]"
echo "=========================================================="

exec $PY_BIN "$DIR/backend/app.py"
