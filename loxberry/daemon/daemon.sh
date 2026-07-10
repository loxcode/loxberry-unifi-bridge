#!/usr/bin/env bash
# LoxBerry startet dieses Skript beim Boot als root.
# Der echte Plugin-Ordner kann einen Suffix tragen (z. B. loxcode_bridge_5c5),
# darum wird er zur Laufzeit ermittelt statt hart verdrahtet.
LBHOME="${LBHOMEDIR:-/opt/loxberry}"
BIN=""
for candidate in "$LBHOME/bin/plugins/loxcode_bridge" "$LBHOME"/bin/plugins/loxcode_bridge_*; do
  [ -d "$candidate" ] || continue
  folder=$(basename "$candidate")
  [ -f "$LBHOME/config/plugins/$folder/config.json" ] || continue
  BIN="$candidate"
  break
done
[ -n "$BIN" ] || { echo "loxcode_bridge: bin-Ordner nicht gefunden"; exit 0; }
FOLDER=$(basename "$BIN")
CONFIG="$LBHOME/config/plugins/$FOLDER/config.json"
LOG="$LBHOME/log/plugins/$FOLDER/bridge.log"
[ -f "$CONFIG" ] || { echo "loxcode_bridge: keine config.json - Daemon nicht gestartet"; exit 0; }
mkdir -p "$(dirname "$LOG")" "$LBHOME/data/plugins/$FOLDER"
chown -R loxberry:loxberry "$(dirname "$LOG")" "$LBHOME/data/plugins/$FOLDER" 2>/dev/null || true
su loxberry -s /bin/bash -c "bash '$BIN/restart.sh'"
exit 0
