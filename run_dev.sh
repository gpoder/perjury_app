#!/usr/bin/env bash
set -e

APP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV="$APP_DIR/venv"
LOGFILE="$APP_DIR/dev.log"
PIDFILE="$APP_DIR/dev.pid"

export PERJURY_DATA_DIR="$APP_DIR/data"

function start_dev() {
    echo "[+] Starting Perjury development server..."

    mkdir -p "$PERJURY_DATA_DIR"

    # Create venv if missing
    if [ ! -d "$VENV" ]; then
        echo "[+] Creating virtual environment..."
        python3 -m venv "$VENV"
    fi

    # Activate venv
    source "$VENV/bin/activate"

    # Install requirements
    echo "[+] Installing dependencies..."
    pip install -r "$APP_DIR/requirements.txt"

    # Stop prior instance if running
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "[+] Killing previous dev instance..."
        kill $(cat "$PIDFILE") || true
        rm -f "$PIDFILE"
    fi

    echo "[+] Launching main.py in background..."
    nohup python "$APP_DIR/main.py" > "$LOGFILE" 2>&1 &

    echo $! > "$PIDFILE"
    echo "[+] Perjury dev server running."
    echo "    PID: $(cat $PIDFILE)"
    echo "    Logs: $LOGFILE"
    echo "    URL:  http://127.0.0.1:5000/"
}

function stop_dev() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "[+] Stopping Perjury dev server..."
        kill $(cat "$PIDFILE") || true
        rm -f "$PIDFILE"
        echo "[+] Stopped."
    else
        echo "[-] No dev server running."
    fi
}

function restart_dev() {
    stop_dev
    start_dev
}

case "$1" in
    start)
        start_dev
        ;;
    stop)
        stop_dev
        ;;
    restart)
        restart_dev
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
        ;;
esac
