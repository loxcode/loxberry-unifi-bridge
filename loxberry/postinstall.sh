#!/bin/bash
# postinstall.sh - laeuft nach dem Kopieren der Plugin-Dateien (Install UND Update).
# Legt die Standard-Konfiguration NUR an, wenn noch keine existiert, damit ein
# Update die vom Nutzer gespeicherte config.json niemals ueberschreibt.
#
#
# Argumente (LoxBerry Plugin-Interface 2.0):
#   $2 = Plugin-Name fuer Skripte
#   $3 = echter Plugin-Installationsordner (FOLDER, evtl. mit Suffix)
PSHNAME="${2:-loxcode_bridge}"
PDIR="${3:-$PSHNAME}"
LBHOME="${5:-${LBHOMEDIR:-/opt/loxberry}}"

if [ -z "$PDIR" ]; then
    PDIR="loxcode_bridge"
fi

CONFIG_BASE="${LBPCONFIG:-$LBHOME/config/plugins}"
BIN_BASE="${LBPBIN:-$LBHOME/bin/plugins}"
DATA_BASE="${LBPDATA:-$LBHOME/data/plugins}"
PCONFIG="$CONFIG_BASE/$PDIR"
PBIN="$BIN_BASE/$PDIR"
PDATA="$DATA_BASE/$PDIR"

mkdir -p "$PCONFIG" "$PDATA"

if [ ! -f "$PCONFIG/config.json" ]; then
    cp "$PBIN/config.default.json" "$PCONFIG/config.json"
    echo "<INFO> Standard-Konfiguration angelegt: $PCONFIG/config.json"
else
    echo "<OK> Bestehende Konfiguration beibehalten: $PCONFIG/config.json"
fi

chmod +x "$PBIN/restart.sh" 2>/dev/null
chown -R loxberry:loxberry "$PCONFIG" "$PDATA" 2>/dev/null || true
chmod 0700 "$PCONFIG" 2>/dev/null || true
chmod 0600 "$PCONFIG/config.json" 2>/dev/null || true
exit 0
