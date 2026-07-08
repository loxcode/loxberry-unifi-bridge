# UniFi Bridge — UniFi-PoE-Gateway für Loxone

Schaltet PoE-Ports **dauerhaft** an/aus und liefert **Status-Feedback**
(PoE-Zustand, Watt je Port, Gerät online) an Loxone — die beiden Dinge,
die ohne Gateway technisch nicht gehen (Session-API + Header-Pflicht,
siehe `../unifi/RECHERCHE.md`).

**Version 1.0 · Docker + LoxBerry · loxcode**

## Varianten

| Variante | Für wen |
|---|---|
| **Docker** | NAS, Server, Proxmox, vorhandener Docker-Host |
| **LoxBerry-Plugin** | Wer schon einen LoxBerry neben dem Miniserver betreibt |

Beide nutzen denselben Kern; Konfiguration überall gleich benannt.

## Schnellstart Docker

```
cd loxcode-bridge
cp docker/docker-compose.example.yml docker/docker-compose.yml
# docker-compose.yml anpassen (UDM-IP, UniFi-User, Switch-MACs, Passwoerter!)
docker compose -f docker/docker-compose.yml up -d --build
curl http://<host>:5000/health   # -> {"status": "ok"}
```

## Schnellstart LoxBerry

```
python3 tools/build_loxberry_zip.py     # erzeugt dist/loxcode_bridge-<version>.zip
```
ZIP über die LoxBerry-Pluginverwaltung installieren, dann im Plugin
„UniFi Bridge" die UniFi-Zugangsdaten eintragen und speichern. Danach:

- **Switches suchen** — Button füllt die Switch-Liste automatisch (Name +
  MAC, mit Modell, PoE-Ports und aktueller Leistung). Kein MAC-Abtippen.
- **Loxone-Vorlagen herunterladen** — Button erzeugt aus den gespeicherten
  Switches ein fertiges ZIP für Loxone Config (Ports automatisch erkannt).
- **Hilfe & Anleitung** — erklärt Zweck, Voraussetzungen, Einrichtung,
  Loxone-Anbindung und typische Fehler direkt im Plugin.
- Ein **Watchdog** (Cronjob, alle 5 Min) startet die Bridge bei Absturz neu.
- Der **Verbindungstest** oben zeigt sofort, ob die UDM erreichbar ist.

## UniFi vorbereiten

Eigenen **lokalen** Benutzer nur für die Bridge anlegen (UniFi OS →
Admins & Benutzer → lokaler Zugang, Rolle mit Geräteverwaltung der
Network-App). Keinen Cloud-Account verwenden.

## HTTP-API

| Endpoint | Beispiel-Antwort |
|---|---|
| `GET /poe/set?switch=Rack&ports=1,2&state=off` | `{"ok":true,"message":"OK"}` |
| `GET /poe/status?switch=Rack&ports=1,2` | `{"ok":true,"ports":{"1":"on","2":"off"}}` |
| `GET /poe/status.txt?switch=Rack&ports=1,2` | `port1=1;port2=0` |
| `GET /poe/power.txt?switch=Rack&ports=1,2` | `port1=4.5;port2=0.0` |
| `GET /device/status.txt?switch=Rack` | `online=1` |
| `GET /devices` | Liste aller PoE-Switches im Controller (Name, MAC, Ports, Watt) |
| `GET /templates.zip?host=<ip>` | Loxone-Vorlagen als ZIP (Ports per Discovery) |
| `GET /selftest` | Kettentest Bridge→UDM (ohne Auth, ohne Secrets) |
| `GET /health` | `{"status":"ok"}` (ohne Auth) |

Alle Endpoints (außer `/health`) mit Basic Auth, wenn `API_USER`/`API_PASS`
gesetzt sind — dringend empfohlen.

## Loxone anbinden

```
python3 tools/make_templates.py --bridge-host <BRIDGE-IP> \
    --api-user loxone --api-pass <PASS> \
    --switch "Rack=aa:bb:cc:dd:ee:ff=1,2,8"
```
Erzeugt in `templates/`:
- `VO_loxcodeBridge.xml` — virtueller Ausgang: je Port ein digitaler
  Aktor (EIN = PoE an, AUS = PoE aus) + „alle Ports" je Switch
- `VI_<Name>_status.xml` / `_power.xml` / `_online.xml` — virtuelle
  HTTP-Eingänge (Polling 30/60 s) mit fertiger Befehlserkennung

In Loxone Config importieren, fertig. PoE-Schalter und Status-Sensoren
verhalten sich wie normale Loxone-Objekte.

## Testen ohne UniFi

`python3 tools/controller_mock.py` startet einen UniFi-Simulator
(User `bridge`/`pw`, 1 Switch) — `UNIFI_HOST` darauf zeigen lassen und
die komplette Kette lokal durchspielen.

## Sicherheit

- Bridge gehört ins LAN, niemals ins Internet exponieren.
- `API_USER`/`API_PASS` setzen; UniFi-User mit minimalen Rechten.
- Keine echten Zugangsdaten in Git — `docker-compose.yml` (ohne
  `.example`) und lokale Configs sind bewusst nicht Teil des Repos.

## Hardware-Testpunkte

1. LoxBerry: Installation des ZIP, Daemon-Start nach Reboot, Webfrontend.
2. Echte UDM: PoE an/aus inkl. `force-provision`-Wirkung, Statuswerte.
3. Loxone: Import der generierten Vorlagen, Befehlserkennung der
   `.txt`-Formate, Polling-Verhalten.

## Lizenz

GNU General Public License v3.0 — siehe [LICENSE](../LICENSE). Wer eine
veränderte Version weitergibt, muss den Quellcode offenlegen.
Bereitgestellt ohne Gewährleistung.

## Credits

**loxcode** — basiert auf einer produktiv erprobten Eigenentwicklung.
