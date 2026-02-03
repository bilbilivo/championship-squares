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
# Usage: ./start_server.sh [--lite|--no-lite] {start|stop|status|restart|setup}
#        --lite     Enable lite mode (reduced visual effects for better performance)
#        --no-lite  Disable lite mode
#        setup      Create a desktop shortcut (.desktop) in this folder

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

VENV_DIR="$SCRIPT_DIR/venv"
PYTHON=${PYTHON:-python3}
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$SCRIPT_DIR/server.pid"
LITE_FILE="$SCRIPT_DIR/.lite_mode"
LOGFILE="$LOG_DIR/server.log"
LITE_MODE=0
LITE_MODE_EXPLICIT=0  # Track if user explicitly set lite mode

# Parse --lite flag
while [[ $# -gt 0 ]]; do
    case "$1" in
        --lite)
            LITE_MODE=1
            LITE_MODE_EXPLICIT=1
            shift
            ;;
        --no-lite)
            LITE_MODE=0
            LITE_MODE_EXPLICIT=1
            shift
            ;;
        *)
            break
            ;;
    esac
done

mkdir -p "$LOG_DIR"

activate_venv() {
    local FIRST_RUN=0
    if [ ! -d "$VENV_DIR" ]; then
        FIRST_RUN=1
        echo "First run — creating virtual environment..."
        if ! "$PYTHON" -m venv "$VENV_DIR"; then
            echo "ERROR: Failed to create virtual environment."
            echo "Make sure python3-venv is installed: sudo apt install python3-venv"
            exit 1
        fi
        # shellcheck disable=SC1090
        . "$VENV_DIR/bin/activate"
        PYTHON="$VENV_DIR/bin/python"

        # Ensure pip is available in the venv
        if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
            echo "pip not found in venv. Installing pip..."
            if ! "$PYTHON" -m ensurepip --upgrade 2>/dev/null; then
                echo "ERROR: Failed to install pip in virtual environment."
                echo "Try: sudo apt install python3-pip python3-venv"
                exit 1
            fi
        fi

        echo "Installing dependencies..."
        if ! "$PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt"; then
            echo "ERROR: Failed to install dependencies."
            echo "Check your internet connection and try again."
            exit 1
        fi

        # Run setup automatically on first run
        echo "Creating desktop shortcut..."
        setup
    elif [ -f "$VENV_DIR/bin/activate" ]; then
        # shellcheck disable=SC1090
        . "$VENV_DIR/bin/activate"
        PYTHON=${PYTHON:-"$VENV_DIR/bin/python"}

        # Ensure pip is available in the venv
        if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
            echo "pip not found in venv. Installing pip..."
            if ! "$PYTHON" -m ensurepip --upgrade 2>/dev/null; then
                echo "ERROR: Failed to install pip in virtual environment."
                echo "Recreating venv. Please run the script again after this completes."
                rm -rf "$VENV_DIR"
                exit 1
            fi
        fi

        # Check if Flask is installed, reinstall dependencies if missing
        if ! "$PYTHON" -c "import flask" 2>/dev/null; then
            echo "Dependencies missing or incomplete. Reinstalling..."
            if ! "$PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt"; then
                echo "ERROR: Failed to install dependencies."
                echo "Try removing the venv folder and running again: rm -rf venv"
                exit 1
            fi
        fi
    fi
    return $FIRST_RUN
}

cleanup_old_logs() {
    # Archive log file if older than 72 hours (3 days)
    if [ -f "$LOGFILE" ]; then
        local LOG_AGE_SECONDS=$(( $(date +%s) - $(date -r "$LOGFILE" +%s 2>/dev/null || echo 0) ))
        local SEVENTY_TWO_HOURS=$((72 * 60 * 60))

        if [ "$LOG_AGE_SECONDS" -gt "$SEVENTY_TWO_HOURS" ]; then
            local ARCHIVE_NAME="$LOG_DIR/server_$(date -r "$LOGFILE" +%Y%m%d_%H%M%S).log"
            mv "$LOGFILE" "$ARCHIVE_NAME"
            echo "Archived old log to: $ARCHIVE_NAME"
        fi
    fi

    # Remove archived logs older than 72 hours
    find "$LOG_DIR" -name "server_*.log" -type f -mtime +3 -delete 2>/dev/null || true
}

open_browser() {
    sleep 1  # Give the server a moment to start
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open http://localhost:8080 &
    elif command -v open >/dev/null 2>&1; then
        open http://localhost:8080
    fi
}

start() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Server already running (pid=$(cat "$PID_FILE"))."
        open_browser
        return 0
    fi

    # Clean up old logs before starting
    cleanup_old_logs

    activate_venv

    if [ "$LITE_MODE" -eq 1 ]; then
        echo "Starting championship-squares (LITE MODE)..."
        # Persist lite mode setting for restarts
        echo "1" > "$LITE_FILE"
        LITE_MODE=1 nohup "$PYTHON" app.py 2>&1 | awk '{ print strftime("[%Y-%m-%d %H:%M:%S]"), $0; fflush(); }' >> "$LOGFILE" &
    else
        echo "Starting championship-squares..."
        # Remove lite mode file if explicitly disabled
        if [ "$LITE_MODE_EXPLICIT" -eq 1 ]; then
            rm -f "$LITE_FILE"
        fi
        nohup "$PYTHON" app.py 2>&1 | awk '{ print strftime("[%Y-%m-%d %H:%M:%S]"), $0; fflush(); }' >> "$LOGFILE" &
    fi
    PID=$!
    echo "$PID" > "$PID_FILE"

    # Verify the server actually started
    sleep 1
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "ERROR: Server failed to start. Check logs: $LOGFILE"
        tail -n 20 "$LOGFILE"

        # Check if it's a missing module error
        if grep -q -E "ModuleNotFoundError|No module named" "$LOGFILE" 2>/dev/null; then
            echo ""
            echo "Detected missing Python module. Reinstalling dependencies..."
            rm -f "$PID_FILE"

            # Ensure pip is available before trying to reinstall
            if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
                echo "pip not available. Attempting to install pip..."
                if ! "$PYTHON" -m ensurepip --upgrade 2>/dev/null; then
                    echo "ERROR: Cannot install pip. Please run: rm -rf venv && ./start_server.sh start"
                    exit 1
                fi
            fi

            if "$PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt"; then
                echo "Dependencies reinstalled. Retrying server start..."

                # Retry starting the server
                if [ "$LITE_MODE" -eq 1 ]; then
                    LITE_MODE=1 nohup "$PYTHON" app.py 2>&1 | awk '{ print strftime("[%Y-%m-%d %H:%M:%S]"), $0; fflush(); }' >> "$LOGFILE" &
                else
                    nohup "$PYTHON" app.py 2>&1 | awk '{ print strftime("[%Y-%m-%d %H:%M:%S]"), $0; fflush(); }' >> "$LOGFILE" &
                fi
                PID=$!
                echo "$PID" > "$PID_FILE"

                sleep 1
                if ! kill -0 "$PID" 2>/dev/null; then
                    echo "ERROR: Server still failed to start after reinstalling dependencies."
                    tail -n 20 "$LOGFILE"
                    rm -f "$PID_FILE"
                    exit 1
                fi

                echo "Started (pid=$PID). Logs: $LOGFILE"
                open_browser
                return 0
            else
                echo "ERROR: Failed to reinstall dependencies."
                exit 1
            fi
        fi

        rm -f "$PID_FILE"
        exit 1
    fi

    echo "Started (pid=$PID). Logs: $LOGFILE"

    # Open browser after starting
    open_browser
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

setup() {
    DESKTOP_FILE="$SCRIPT_DIR/championship-squares.desktop"
    ICON_FILE="$SCRIPT_DIR/icon.png"

    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=Championship Squares
Comment=Launch Championship Squares game
Icon=$ICON_FILE
Exec="$SCRIPT_DIR/start_server.sh" start
Terminal=false
EOF

    chmod +x "$DESKTOP_FILE"
    echo "Desktop shortcut created: $DESKTOP_FILE"
    echo "Double-click it from this folder to launch the game."
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
        # Preserve previous lite mode setting if no explicit flag given
        if [ "$LITE_MODE_EXPLICIT" -eq 0 ] && [ -f "$LITE_FILE" ]; then
            LITE_MODE=1
        fi
        stop || true
        start
        ;;
    setup)
        setup
        ;;
    *)
        echo "Usage: $0 [--lite|--no-lite] {start|stop|status|restart|setup}"
        echo "       --lite     Enable lite mode (reduced visual effects)"
        echo "       --no-lite  Disable lite mode (full visual effects)"
        echo "       setup      Create a desktop shortcut (.desktop) in this folder"
        exit 2
        ;;
esac
