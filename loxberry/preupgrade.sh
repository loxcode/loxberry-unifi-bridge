#!/usr/bin/env bash
# preupgrade.sh - laeuft vor dem Kopieren der neuen Plugin-Dateien.
# Sichert die bestehende Nutzer-Konfiguration, weil LoxBerry beim Update
# Plugin-Verzeichnisse neu anlegen kann.
#
# Argumente (LoxBerry Plugin-Interface 2.0):
#   $1 = Temp-Ordnername
#   $2 = Plugin-Name fuer Skripte
#   $3 = echter Plugin-Installationsordner (FOLDER, evtl. mit Suffix)
#   $4 = Plugin-Version
#   $5 = LoxBerry-Home
#   $6 = voller Temp-Pfad (bei neueren LoxBerry-Versionen)
PTEMPDIR="${1:-}"
PSHNAME="${2:-loxcode_bridge}"
PDIR="${3:-$PSHNAME}"
LBHOME="${5:-${LBHOMEDIR:-/opt/loxberry}}"
PTEMPPATH="${6:-}"

if [ -z "$PDIR" ]; then
    PDIR="loxcode_bridge"
fi
if [ -z "$PTEMPPATH" ]; then
    if [ -n "$PTEMPDIR" ]; then
        PTEMPPATH="/tmp/${PTEMPDIR}_upgrade"
    else
        PTEMPPATH="/tmp/loxcode_bridge_upgrade"
    fi
fi

CONFIG_BASE="${LBPCONFIG:-$LBHOME/config/plugins}"
PCONFIG="$CONFIG_BASE/$PDIR"
BACKUP="$PTEMPPATH/config/$PDIR"

echo "<INFO> Sichere bestehende Konfiguration aus $PCONFIG"

if [ ! -d "$PCONFIG" ]; then
    echo "<INFO> Keine bestehende Konfiguration gefunden."
    exit 0
fi

mkdir -p "$BACKUP" || {
    echo "<ERROR> Backup-Ordner konnte nicht angelegt werden: $BACKUP"
    exit 1
}

cp -pR "$PCONFIG/." "$BACKUP/" || {
    echo "<ERROR> Konfiguration konnte nicht gesichert werden."
    exit 1
}

echo "<OK> Konfiguration gesichert: $BACKUP"
exit 0
