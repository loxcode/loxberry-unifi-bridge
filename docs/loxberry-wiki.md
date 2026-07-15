# LoxBerry Wiki Draft: UniFi Bridge

Zielseite: https://wiki.loxberry.de/plugins/unifi_bridge/start

Wiki-ID: `plugins:unifi_bridge:start`

Nach LoxBerry-Wiki-Vorgabe wird für ein neues Plugin ein eigenes
Unterverzeichnis unter `plugins` angelegt. Für dieses Plugin ist das
Unterverzeichnis `unifi_bridge` vorgesehen.

## Pluginübersicht-Datenfelder

Diese Werte müssen im Wiki unterhalb des Editorfensters in den
`pluginübersicht`-Datenfeldern gepflegt werden.

| Feld | Wert |
| --- | --- |
| Autor | LOXCODE |
| Logo | `plugins:unifi_bridge:icon_128.png` |
| Status | STABLE |
| Version | 1.0.19 |
| Min. LB Version | 2.0.0 |
| Release Download | https://github.com/loxcode/loxberry-unifi-bridge/releases/download/v1.0.19/loxcode_bridge-1.0.19.zip |
| Pre-Release Download |  |
| Beschreibung | UniFi Bridge schaltet UniFi-PoE-Ports aus Loxone und liefert Statuswerte wie PoE-Zustand, Leistung und Online-Status zurück. |
| Sprachen | DE |
| Diskussion | https://github.com/loxcode/loxberry-unifi-bridge/issues |

Logo-Upload: `loxberry/icons/icon_128.png` in den Wiki-Namespace
`plugins:unifi_bridge` hochladen und im Logo-Feld als
`plugins:unifi_bridge:icon_128.png` auswählen.

## DokuWiki-Quelltext

```dokuwiki
====== UniFi Bridge ======

===== Kurzbeschreibung =====

UniFi Bridge ist ein LoxBerry-Plugin, das UniFi-PoE-Switches über Loxone steuerbar macht. Das Plugin schaltet PoE-Ports dauerhaft ein oder aus und liefert Statuswerte wie PoE-Zustand, Leistung pro Port und Switch-Online-Status an Loxone zurück.

===== Funktionen =====

  * PoE-Ports über HTTP-API aus Loxone schalten
  * Statuswerte als JSON- und Text-Endpunkte
  * Switch-Autoerkennung über UniFi Controller oder UDM
  * Loxone-Vorlagen direkt aus dem Plugin erzeugen und herunterladen
  * Verbindungstest und Selftest für die UniFi-Anbindung
  * Update-sichere LoxBerry-Konfiguration
  * Watchdog für den Bridge-Dienst
  * Automatische Updates über GitHub-Releases

===== Voraussetzungen =====

  * LoxBerry 2.x oder neuer
  * UniFi Controller oder UDM im lokalen Netzwerk
  * Lokaler UniFi-Benutzer mit Zugriff auf die Network-App
  * UniFi-Switch mit PoE-Ports
  * Freier Service-Port, Standard ist 5000

===== Installation =====

Das Plugin-ZIP herunterladen und über die LoxBerry-Pluginverwaltung installieren:

  * [[https://github.com/loxcode/loxberry-unifi-bridge/releases/latest|Aktuelle Version]]
  * [[https://github.com/loxcode/loxberry-unifi-bridge/releases/download/v1.0.19/loxcode_bridge-1.0.19.zip|Direktdownload 1.0.19]]

Nach der Installation ist die Pluginseite in der LoxBerry-Pluginverwaltung unter **UniFi Bridge** erreichbar.

===== UniFi vorbereiten =====

In UniFi OS einen eigenen lokalen Benutzer nur für die Bridge anlegen. Der Benutzer braucht Zugriff auf die Network-App und sollte nur die notwendigen Rechte für die Geräteverwaltung erhalten. Ein Cloud-Account ist für den Betrieb nicht empfohlen.

===== Konfiguration =====

  - Pluginseite **UniFi Bridge** öffnen
  - UniFi Host, Site, Benutzer und Passwort eintragen
  - API-Benutzer und API-Passwort für Loxone setzen
  - Speichern und Bridge neu starten
  - **Switches suchen** ausführen und erkannte Switches speichern
  - **Loxone-Vorlagen herunterladen** und in Loxone Config importieren

Die Nutzerkonfiguration bleibt bei Plugin-Updates erhalten.

===== Loxone-Anbindung =====

Die Bridge stellt HTTP-Endpunkte bereit. Beispiel zum Ausschalten von Port 1 und 2 am Switch `Rack`:

<code>
http://LOXBERRY:5000/poe/set?switch=Rack&ports=1,2&state=off
</code>

Statusabfrage als Text für virtuelle Eingänge:

<code>
http://LOXBERRY:5000/poe/status.txt?switch=Rack&ports=1,2
</code>

Wenn API-Zugangsdaten gesetzt sind, muss Loxone Basic Auth verwenden.

===== Wichtige Endpunkte =====

^ Endpoint ^ Zweck ^
| `/health` | Dienststatus ohne Auth |
| `/selftest` | Verbindungstest Bridge zu UniFi |
| `/devices` | Erkannte PoE-Switches ausgeben |
| `/poe/set` | PoE-Port schalten |
| `/poe/status` | PoE-Status als JSON |
| `/poe/status.txt` | PoE-Status als Text |
| `/poe/power.txt` | PoE-Leistung als Text |
| `/device/status.txt` | Switch-Online-Status als Text |
| `/templates.zip` | Loxone-Vorlagen herunterladen |

===== Automatische Updates =====

Das Plugin unterstützt automatische Updates über die LoxBerry-Pluginverwaltung. Die Release-Konfiguration liegt hier:

<code>
https://raw.githubusercontent.com/loxcode/loxberry-unifi-bridge/main/loxberry/release.cfg
</code>

===== Sicherheit =====

  * Bridge nur im lokalen Netzwerk betreiben
  * Service nicht direkt ins Internet freigeben
  * API-Benutzer und API-Passwort setzen
  * UniFi-Benutzer mit minimal notwendigen Rechten verwenden
  * Keine echten Zugangsdaten in Loxone-Vorlagen oder Screenshots veröffentlichen

===== Hilfe und Fehleranalyse =====

Die Pluginseite enthält **Hilfe & Anleitung** mit Einrichtung, Loxone-Beispielen und typischen Fehlern. Für Fehlerberichte bitte ein Issue im GitHub-Repository anlegen:

[[https://github.com/loxcode/loxberry-unifi-bridge/issues]]

===== Links =====

  * [[https://github.com/loxcode/loxberry-unifi-bridge|GitHub Repository]]
  * [[https://github.com/loxcode/loxberry-unifi-bridge/releases|Releases]]
```
