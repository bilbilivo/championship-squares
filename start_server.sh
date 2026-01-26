#!/usr/bin/env bash
# If invoked under /bin/sh (dash), re-exec with bash so `pipefail` is available.
if [ -z "${BASH_VERSION:-}" ]; then
    if command -v bash >/dev/null 2>&1; then
        exec bash "$0" "$@"
    else
        echo "This script requires bash. Please run with bash." >&2
        exit 1
    fi
fi

set -euo pipefail

# start_server.sh - simple launcher that activates the repository venv
# Usage: ./start_server.sh [--lite] start|stop|status|restart
#        --lite  Enable lite mode (reduced visual effects for better performance)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

VENV_DIR="$SCRIPT_DIR/venv"
PYTHON=${PYTHON:-python3}
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$SCRIPT_DIR/server.pid"
LITE_FILE="$SCRIPT_DIR/.lite_mode"
LOGFILE="$LOG_DIR/server.log"
LITE_MODE=0

# Parse --lite flag
while [[ $# -gt 0 ]]; do
    case "$1" in
        --lite)
            LITE_MODE=1
            shift
            ;;
        --no-lite)
            LITE_MODE=0
            # Remove lite mode file if switching back
            rm -f "$LITE_FILE"
            shift
            ;;
        *)
            break
            ;;
    esac
done

mkdir -p "$LOG_DIR"

activate_venv() {
    if [ -f "$VENV_DIR/bin/activate" ]; then
        # shellcheck disable=SC1090
        . "$VENV_DIR/bin/activate"
        PYTHON=${PYTHON:-"$VENV_DIR/bin/python"}
    fi
}

start() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Server already running (pid=$(cat "$PID_FILE"))."
        return 0
    fi

    activate_venv

    # Check for persisted lite mode if not explicitly set on command line
    if [ "$LITE_MODE" -eq 0 ] && [ -f "$LITE_FILE" ]; then
        LITE_MODE=1
    fi

    if [ "$LITE_MODE" -eq 1 ]; then
        echo "Starting championship-squares (LITE MODE)..."
        # Persist lite mode setting for restarts
        echo "1" > "$LITE_FILE"
        LITE_MODE=1 nohup "$PYTHON" app.py >> "$LOGFILE" 2>&1 &
    else
        echo "Starting championship-squares..."
        # Remove lite mode file if starting in normal mode
        rm -f "$LITE_FILE"
        nohup "$PYTHON" app.py >> "$LOGFILE" 2>&1 &
    fi
    PID=$!
    echo "$PID" > "$PID_FILE"
    echo "Started (pid=$PID). Logs: $LOGFILE"
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "No pid file found. Is the server running?"
        return 1
    fi
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping server (pid=$PID)..."
        kill "$PID"
        sleep 1
        rm -f "$PID_FILE"
        echo "Stopped."
    else
        echo "Process $PID not running. Removing stale pid file."
        rm -f "$PID_FILE"
    fi
}

status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            if [ -f "$LITE_FILE" ]; then
                echo "Running in LITE MODE (pid=$PID). Logs: $LOGFILE"
            else
                echo "Running (pid=$PID). Logs: $LOGFILE"
            fi
            return 0
        else
            echo "Stale pid file found (pid=$PID)."
            return 1
        fi
    else
        echo "Not running."
        return 3
    fi
}

ACTION="${1:-start}"
case "$ACTION" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    restart)
        stop || true
        start
        ;;
    *)
        echo "Usage: $0 [--lite|--no-lite] {start|stop|status|restart}"
        echo "       --lite     Enable lite mode (reduced visual effects)"
        echo "       --no-lite  Disable lite mode (full visual effects)"
        exit 2
        ;;
esac
