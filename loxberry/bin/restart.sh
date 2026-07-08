#!/usr/bin/env bash
# Bridge neu starten (vom Webfrontend als User loxberry aufgerufen).
# Ordnername und LoxBerry-Home werden aus dem eigenen Pfad abgeleitet:
# dieses Skript liegt in <LBHOME>/bin/plugins/<ordner>/restart.sh
BIN="$(cd "$(dirname "$0")" && pwd)"
FOLDER="$(basename "$BIN")"
LBHOME="$(dirname "$(dirname "$(dirname "$BIN")")")"
CONFIG="$LBHOME/config/plugins/$FOLDER/config.json"
LOG="$LBHOME/log/plugins/$FOLDER/bridge.log"
pkill -f "loxcode_bridge.*app\.py" 2>/dev/null
sleep 1
mkdir -p "$(dirname "$LOG")"
BRIDGE_CONFIG="$CONFIG" nohup python3 "$BIN/app.py" >> "$LOG" 2>&1 &
echo "restarted (Log: $LOG)"
