#!/usr/bin/env bash
# Bridge kontrolliert ueber Gunicorn neu starten.
set -eu

BIN="$(cd "$(dirname "$0")" && pwd)"
FOLDER="$(basename "$BIN")"
LBHOME="$(dirname "$(dirname "$(dirname "$BIN")")")"
CONFIG="$LBHOME/config/plugins/$FOLDER/config.json"
DATA="$LBHOME/data/plugins/$FOLDER"
LOG="$LBHOME/log/plugins/$FOLDER/bridge.log"
PID="$DATA/bridge.pid"
LOCK="$DATA/restart.lock"

mkdir -p "$DATA" "$(dirname "$LOG")"

is_bridge_process() {
    process_pid="$1"
    case "$process_pid" in
        ''|*[!0-9]*) return 1 ;;
    esac
    [ "$process_pid" != "$$" ] || return 1
    [ -r "/proc/$process_pid/cmdline" ] || return 1
    process_cmdline="$(tr '\0' ' ' < "/proc/$process_pid/cmdline" 2>/dev/null || true)"
    case "$process_cmdline" in
        *"$BIN/app.py"*|*gunicorn*"$BIN"*app:application*) return 0 ;;
        *) return 1 ;;
    esac
}

stop_bridge_process() {
    process_pid="$1"
    is_bridge_process "$process_pid" || return 1
    kill "$process_pid" 2>/dev/null || return 1
    for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
        kill -0 "$process_pid" 2>/dev/null || return 0
        sleep 0.2
    done
    if is_bridge_process "$process_pid"; then
        kill -KILL "$process_pid" 2>/dev/null || true
    fi
}

stop_known_processes() {
    if [ -f "$PID" ]; then
        old_pid="$(cat "$PID" 2>/dev/null || true)"
        if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
            if ! stop_bridge_process "$old_pid"; then
                echo "PID-Datei gehoert nicht zur UniFi Bridge oder der Prozess darf nicht beendet werden." >&2
            fi
        fi
        rm -f "$PID"
    fi

    # Migration von Versionen, die python3 app.py ohne PID-Datei starteten.
    for process_dir in /proc/[0-9]*; do
        [ -d "$process_dir" ] || continue
        process_pid="${process_dir##*/}"
        if is_bridge_process "$process_pid"; then
            echo "Beende alte UniFi-Bridge-Instanz (PID $process_pid)."
            stop_bridge_process "$process_pid" || true
        fi
    done
}

# Cron und Upgrade-Hooks koennen als root laufen. Alte Instanzen duerfen dann
# beendet werden, der neue Netzwerkdienst laeuft danach immer als loxberry.
if [ "$(id -u)" -eq 0 ] && id loxberry >/dev/null 2>&1; then
    stop_known_processes
    chown -R loxberry:loxberry "$DATA" "$(dirname "$LOG")" 2>/dev/null || true
    exec su loxberry -s /bin/bash -c "exec bash '$BIN/restart.sh'"
fi

exec 9>"$LOCK"
if command -v flock >/dev/null 2>&1; then
    if ! flock -w 15 9; then
        # 1.0.18 vererbte den Lock versehentlich an Gunicorn. Nach Ablauf der
        # regulaeren Wartezeit beenden wir nur eigene Bridge-Prozesse und
        # uebernehmen den dadurch freigegebenen Lock.
        echo "Festgehaltenen Restart-Lock einer alten Bridge-Instanz loesen."
        stop_known_processes
        flock -w 10 9 || {
            echo "Ein anderer Neustart der UniFi Bridge laeuft bereits." >&2
            exit 1
        }
    fi
fi

if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 5242880 ]; then
    mv -f "$LOG" "$LOG.1"
fi

stop_known_processes

[ -f "$CONFIG" ] || { echo "Konfiguration fehlt: $CONFIG" >&2; exit 1; }

SETTINGS="$(python3 - "$CONFIG" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    cfg = json.load(handle)
port = int(cfg.get("BRIDGE_PORT", 5000))
if not 1 <= port <= 65535:
    raise SystemExit("ungueltiger Port")
bind = str(cfg.get("BRIDGE_BIND", "0.0.0.0"))
if bind not in ("0.0.0.0", "127.0.0.1"):
    raise SystemExit("Bind-Adresse muss 0.0.0.0 oder 127.0.0.1 sein")
print(port, bind)
PY
)"
set -- $SETTINGS
PORT="$1"
BIND="$2"

EXPECTED_VERSION="$(python3 - "$BIN/app.py" <<'PY'
import ast, sys
tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
for node in tree.body:
    if isinstance(node, ast.Assign):
        if any(isinstance(target, ast.Name) and target.id == "APP_VERSION"
               for target in node.targets):
            print(ast.literal_eval(node.value))
            break
else:
    raise SystemExit("APP_VERSION fehlt")
PY
)"

python3 - "$BIND" "$PORT" <<'PY'
import socket, sys

bind, port = sys.argv[1], int(sys.argv[2])
sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sock.bind((bind, port))
except OSError as exc:
    print(f"Port {port} ist bereits durch einen anderen Dienst belegt: {exc}",
          file=sys.stderr)
    raise SystemExit(1)
finally:
    sock.close()
PY

BRIDGE_CONFIG="$CONFIG" python3 -m gunicorn \
    --chdir "$BIN" \
    --bind "$BIND:$PORT" \
    --workers 1 \
    --threads 4 \
    --timeout 60 \
    --access-logfile /dev/null \
    --error-logfile "$LOG" \
    --pid "$PID" \
    --daemon \
    app:application 9>&-

if ! python3 - "$PORT" "$EXPECTED_VERSION" <<'PY'
import json, sys, time, urllib.request
port = int(sys.argv[1])
expected_version = sys.argv[2]
last_error = ""
for _ in range(20):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
            data = json.loads(response.read().decode("utf-8"))
        if (data.get("service") == "unifi_bridge"
                and data.get("status") == "ok"
                and data.get("version") == expected_version):
            raise SystemExit(0)
        last_error = "auf dem Port antwortet eine andere oder alte Dienstversion"
    except Exception as exc:
        last_error = str(exc)
    time.sleep(0.25)
print("Healthcheck fehlgeschlagen: " + last_error, file=sys.stderr)
raise SystemExit(1)
PY
then
    failed_pid="$(cat "$PID" 2>/dev/null || true)"
    if [ -n "$failed_pid" ]; then
        stop_bridge_process "$failed_pid" || true
    fi
    rm -f "$PID"
    echo "Bridge konnte nicht gestartet werden. Letzte Logzeilen:" >&2
    tail -n 40 "$LOG" >&2 2>/dev/null || true
    exit 1
fi

echo "restarted on port $PORT (Log: $LOG)"
