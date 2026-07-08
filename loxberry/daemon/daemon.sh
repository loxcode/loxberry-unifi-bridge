#!/usr/bin/env bash
# LoxBerry startet dieses Skript beim Boot als root.
# Der echte Plugin-Ordner kann einen Suffix tragen (z. B. loxcode_bridge_5c5),
# darum wird er zur Laufzeit ermittelt statt hart verdrahtet.
LBHOME="${LBHOMEDIR:-/opt/loxberry}"
BIN=$(ls -d "$LBHOME"/bin/plugins/loxcode_bridge* 2>/dev/null | head -1)
[ -n "$BIN" ] || { echo "loxcode_bridge: bin-Ordner nicht gefunden"; exit 0; }
FOLDER=$(basename "$BIN")
CONFIG="$LBHOME/config/plugins/$FOLDER/config.json"
LOG="$LBHOME/log/plugins/$FOLDER/bridge.log"
[ -f "$CONFIG" ] || { echo "loxcode_bridge: keine config.json - Daemon nicht gestartet"; exit 0; }
mkdir -p "$(dirname "$LOG")"
chown loxberry:loxberry "$(dirname "$LOG")" 2>/dev/null
su loxberry -s /bin/bash -c \
  "BRIDGE_CONFIG='$CONFIG' python3 '$BIN/app.py' >> '$LOG' 2>&1 &"
exit 0
