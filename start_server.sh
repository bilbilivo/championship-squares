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
# Usage: ./start_server.sh [--lite|--no-lite] {start|stop|status|restart|install|uninstall}
#        --lite      Enable lite mode (reduced visual effects for better performance)
#        --no-lite   Disable lite mode
#        install     Create a desktop shortcut (.desktop) and install to Applications menu
#        uninstall   Remove the desktop shortcut from this folder and Applications menu

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
    local BOOTSTRAP_PYTHON="$PYTHON"

    if [ -d "$VENV_DIR" ] && { [ ! -f "$VENV_DIR/pyvenv.cfg" ] || [ ! -x "$VENV_DIR/bin/python" ]; }; then
        echo "Existing virtual environment is incomplete. Recreating..."
        rm -rf "$VENV_DIR"
    fi

    if [ ! -d "$VENV_DIR" ]; then
        FIRST_RUN=1
        echo "First run — creating virtual environment..."
        if ! "$BOOTSTRAP_PYTHON" -m venv "$VENV_DIR"; then
            echo "ERROR: Failed to create virtual environment."
            echo "Make sure python3-venv is installed: sudo apt install python3-venv"
            exit 1
        fi
        PYTHON="$VENV_DIR/bin/python"
    else
        PYTHON="$VENV_DIR/bin/python"
    fi

    if [ ! -x "$PYTHON" ]; then
        echo "ERROR: Virtual environment is missing its Python executable."
        echo "Try removing the venv folder and running again: rm -rf venv"
        exit 1
    fi

    # Ensure pip is available in the venv
    if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
        echo "pip not found in venv. Installing pip..."
        if ! "$PYTHON" -m ensurepip --upgrade 2>/dev/null; then
            if [ "$FIRST_RUN" -eq 0 ]; then
                echo "Existing virtual environment cannot be repaired. Recreating..."
                rm -rf "$VENV_DIR"
                FIRST_RUN=1

                echo "Creating virtual environment..."
                if ! "$BOOTSTRAP_PYTHON" -m venv "$VENV_DIR"; then
                    echo "ERROR: Failed to recreate virtual environment."
                    echo "Make sure python3-venv is installed: sudo apt install python3-venv"
                    exit 1
                fi

                PYTHON="$VENV_DIR/bin/python"
            fi

            if ! "$PYTHON" -m ensurepip --upgrade 2>/dev/null; then
                echo "ERROR: Failed to install pip in virtual environment."
                echo "Try: sudo apt install python3-venv"
                echo "If your distro uses a minimal Python package, you may also need: sudo apt install python3-full"
                exit 1
            fi
        fi
    fi

    if [ "$FIRST_RUN" -eq 1 ]; then
        echo "Installing dependencies..."
        if ! "$PYTHON" -m pip install "$SCRIPT_DIR"; then
            echo "ERROR: Failed to install dependencies."
            echo "Check your internet connection and try again."
            exit 1
        fi

        # Run install automatically on first run
        echo "Creating desktop shortcut..."
        install
    else
        # Check runtime dependencies, including upgrades to an existing install.
        if ! "$PYTHON" -c "import flask, qrcode" 2>/dev/null; then
            echo "Dependencies missing or incomplete. Reinstalling..."
            if ! "$PYTHON" -m pip install "$SCRIPT_DIR"; then
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
    sleep 1.5  # Give the server a moment to start
    if command -v xdg-open >/dev/null 2>&1; then
        NO_AT_BRIDGE=1 xdg-open http://localhost:8080 >/dev/null 2>&1 &
    elif command -v open >/dev/null 2>&1; then
        open http://localhost:8080
    fi
}

start() {
    local RECENT_LOG=""
    local LOG_START_SIZE=0

    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Server already running (pid=$(cat "$PID_FILE"))."
        open_browser
        return 0
    fi

    # Clean up old logs before starting
    cleanup_old_logs

    if [ -f "$LOGFILE" ]; then
        LOG_START_SIZE=$(wc -c < "$LOGFILE" 2>/dev/null || echo 0)
    fi

    activate_venv

    if [ "$LITE_MODE" -eq 1 ]; then
        echo "Starting championship-squares (LITE MODE)..."
        # Persist lite mode setting for restarts
        echo "1" > "$LITE_FILE"
        LITE_MODE=1 nohup "$PYTHON" app.py >> "$LOGFILE" 2>&1 &
    else
        echo "Starting championship-squares..."
        # Remove lite mode file when starting in normal mode
        rm -f "$LITE_FILE"
        nohup "$PYTHON" app.py >> "$LOGFILE" 2>&1 &
    fi
    PID=$!
    echo "$PID" > "$PID_FILE"

    # Verify the server actually started
    sleep 1
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "ERROR: Server failed to start. Check logs: $LOGFILE"
        if [ -f "$LOGFILE" ]; then
            RECENT_LOG="$(tail -c +"$((LOG_START_SIZE + 1))" "$LOGFILE" 2>/dev/null || true)"
            if [ -z "$RECENT_LOG" ]; then
                RECENT_LOG="$(tail -n 50 "$LOGFILE" 2>/dev/null || true)"
            fi
        fi
        if [ -n "$RECENT_LOG" ]; then
            printf '%s\n' "$RECENT_LOG"
        fi

        # Check if it's a port conflict error
        if printf '%s\n' "$RECENT_LOG" | grep -q -E "Address already in use|port.*already.*in use"; then
            echo ""
            echo "ERROR: Port 8080 is already in use by another program."
            echo ""
            echo "To resolve this:"
            echo ""
            echo "1. Find what's using the port:"
            echo "   sudo lsof -i :8080"
            echo "   (or: sudo netstat -tulpn | grep 8080)"
            echo ""
            echo "2. Stop the process (replace PID with actual process ID):"
            echo "   kill <PID>"
            echo "   (or: sudo kill <PID> if you don't own the process)"
            echo ""
            echo "3. Or change the port in config.py to use a different port"
            rm -f "$PID_FILE"
            exit 1
        fi

        # Check if it's a missing module error
        if printf '%s\n' "$RECENT_LOG" | grep -q -E "ModuleNotFoundError|No module named"; then
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

            if "$PYTHON" -m pip install "$SCRIPT_DIR"; then
                echo "Dependencies reinstalled. Retrying server start..."

                # Retry starting the server
                if [ "$LITE_MODE" -eq 1 ]; then
                    LITE_MODE=1 nohup "$PYTHON" app.py >> "$LOGFILE" 2>&1 &
                else
                    nohup "$PYTHON" app.py >> "$LOGFILE" 2>&1 &
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

install() {
    DESKTOP_FILE="$SCRIPT_DIR/championship-squares.desktop"
    ICON_FILE="$SCRIPT_DIR/icon.png"
    APPS_DIR="$HOME/.local/share/applications"

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

    # Install to Applications menu
    mkdir -p "$APPS_DIR"
    if cp "$DESKTOP_FILE" "$APPS_DIR/"; then
        echo "Installed to Applications menu: $APPS_DIR/championship-squares.desktop"
        # Update desktop database (ignore errors if update-desktop-database not available)
        if command -v update-desktop-database >/dev/null 2>&1; then
            update-desktop-database "$APPS_DIR" 2>/dev/null || true
        fi
        echo ""
        echo "✓ Championship Squares is now available in your Applications menu!"
        echo "  - Press Super (Windows key) and search for 'Championship' or 'Squares' to find it."
    else
        echo "Could not install to Applications menu"
        echo "Local shortcut: $DESKTOP_FILE (right-click → 'Allow Launching' to use)"
    fi
}

uninstall() {
    DESKTOP_FILE="$SCRIPT_DIR/championship-squares.desktop"
    APPS_DIR="$HOME/.local/share/applications"
    APPS_DESKTOP="$APPS_DIR/championship-squares.desktop"
    local removed=0

    if [ -f "$APPS_DESKTOP" ]; then
        rm -f "$APPS_DESKTOP"
        echo "Removed from Applications menu: $APPS_DESKTOP"
        if command -v update-desktop-database >/dev/null 2>&1; then
            update-desktop-database "$APPS_DIR" 2>/dev/null || true
        fi
        removed=1
    fi

    if [ -f "$DESKTOP_FILE" ]; then
        rm -f "$DESKTOP_FILE"
        echo "Removed local shortcut: $DESKTOP_FILE"
        removed=1
    fi

    if [ "$removed" -eq 0 ]; then
        echo "No desktop shortcut found to remove."
    else
        echo "✓ Championship Squares has been removed from your Applications menu."
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
        # Preserve previous lite mode setting if no explicit flag given
        if [ "$LITE_MODE_EXPLICIT" -eq 0 ] && [ -f "$LITE_FILE" ]; then
            LITE_MODE=1
        fi
        stop || true
        start
        ;;
    install)
        install
        ;;
    uninstall)
        uninstall
        ;;
    *)
        echo "Usage: $0 [--lite|--no-lite] {start|stop|status|restart|install|uninstall}"
        echo "       --lite      Enable lite mode (reduced visual effects)"
        echo "       --no-lite   Disable lite mode (full visual effects)"
        echo "       install     Create a desktop shortcut (.desktop) and install to Applications menu"
        echo "       uninstall   Remove the desktop shortcut from this folder and Applications menu"
        exit 2
        ;;
esac
