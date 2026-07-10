#!/usr/bin/env bash
# postupgrade.sh - laeuft nach postinstall.sh als letzter Update-Schritt.
# Stellt die in preupgrade.sh gesicherte Nutzer-Konfiguration wieder her.
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
BIN_BASE="${LBPBIN:-$LBHOME/bin/plugins}"
DATA_BASE="${LBPDATA:-$LBHOME/data/plugins}"
PCONFIG="$CONFIG_BASE/$PDIR"
PBIN="$BIN_BASE/$PDIR"
PDATA="$DATA_BASE/$PDIR"
BACKUP="$PTEMPPATH/config/$PDIR"

mkdir -p "$PCONFIG" || {
    echo "<ERROR> Konfigurationsordner konnte nicht angelegt werden: $PCONFIG"
    exit 1
}

if [ -d "$BACKUP" ]; then
    echo "<INFO> Stelle gesicherte Konfiguration wieder her: $BACKUP"
    cp -pR "$BACKUP/." "$PCONFIG/" || {
        echo "<ERROR> Konfiguration konnte nicht wiederhergestellt werden."
        exit 1
    }
    echo "<OK> Bestehende Konfiguration wiederhergestellt: $PCONFIG"
elif [ ! -f "$PCONFIG/config.json" ] && [ -f "$PBIN/config.default.json" ]; then
    cp "$PBIN/config.default.json" "$PCONFIG/config.json" || {
        echo "<ERROR> Standard-Konfiguration konnte nicht angelegt werden."
        exit 1
    }
    echo "<INFO> Keine Backup-Konfiguration gefunden; Standard-Konfiguration angelegt."
else
    echo "<OK> Keine Backup-Konfiguration gefunden; vorhandene Konfiguration beibehalten."
fi

chmod +x "$PBIN/restart.sh" 2>/dev/null
mkdir -p "$PDATA"
chown -R loxberry:loxberry "$PCONFIG" "$PDATA" 2>/dev/null || true
chmod 0700 "$PCONFIG" 2>/dev/null || true
chmod 0600 "$PCONFIG/config.json" 2>/dev/null || true

if [ -n "$PTEMPPATH" ] && [ -d "$PTEMPPATH" ]; then
    SAFE_TEMP="$(realpath -m "$PTEMPPATH" 2>/dev/null || true)"
    case "$SAFE_TEMP" in
        /tmp/*|/var/tmp/*) rm -rf "$SAFE_TEMP" ;;
        *) echo "<INFO> Temp-Ordner wird aus Sicherheitsgruenden nicht geloescht: $PTEMPPATH" ;;
    esac
fi

if [ "${LOXBERRY_SKIP_RESTART:-0}" != "1" ] && [ -x "$PBIN/restart.sh" ]; then
    echo "<INFO> Starte UniFi Bridge mit der neuen Version neu."
    if ! bash "$PBIN/restart.sh"; then
        echo "<ERROR> UniFi Bridge konnte nach dem Update nicht gestartet werden."
        exit 1
    fi
fi

exit 0
