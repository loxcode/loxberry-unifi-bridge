<?php
// UniFi Bridge (LOXCODE) - Hilfeseite
@include_once "loxberry_system.php";
@include_once "loxberry_web.php";

if (!headers_sent()) {
    header('Content-Type: text/html; charset=utf-8');
}

if (class_exists('LBWeb')) {
    LBWeb::lbheader("UniFi Bridge Hilfe", "https://github.com/loxcode", "", true);
}
?>
<style>
.ucb-help{max-width:920px;margin:0 auto;padding:14px;color:#1f2933;line-height:1.45;}
.ucb-help h2{margin:0 0 4px;font-size:28px;line-height:1.2;}
.ucb-help h3{margin:24px 0 8px;font-size:18px;}
.ucb-help p{margin:8px 0;}
.ucb-help ul,.ucb-help ol{margin:8px 0 12px 22px;padding:0;}
.ucb-help li{margin:5px 0;}
.ucb-help code{background:#f4f6f8;border:1px solid #d8dde3;border-radius:3px;padding:1px 4px;}
.ucb-help pre{background:#f8fafc;border:1px solid #d8dde3;border-radius:4px;padding:10px;overflow:auto;}
.ucb-help table{width:100%;border-collapse:collapse;margin:8px 0 14px;}
.ucb-help th,.ucb-help td{border-bottom:1px solid #e5e9ee;padding:8px 6px;text-align:left;vertical-align:top;}
.ucb-help th{background:#f4f6f8;color:#39424e;}
.ucb-lead{color:#4b5563;max-width:72ch;}
.ucb-actions{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 18px;}
.ucb-btn{display:inline-block;border:1px solid #9aa6b2;border-radius:4px;background:#fff;color:#111!important;text-decoration:none!important;padding:8px 12px;font-weight:bold;}
.ucb-note{background:#f7fbf5;border:1px solid #cfe1c8;border-radius:4px;padding:10px 12px;margin:12px 0;}
@media (max-width:720px){.ucb-help{padding:10px}.ucb-help table{font-size:13px}}
</style>

<div class="ucb-help">
  <div class="ucb-actions">
    <a class="ucb-btn" href="index.php">Zur Konfiguration</a>
  </div>

  <h2>UniFi Bridge <small style="font-weight:normal;color:#667085;">by LOXCODE</small></h2>
  <p class="ucb-lead">Dieses Plugin verbindet Loxone mit UniFi-Switches. Es schaltet PoE-Ports dauerhaft ein oder aus und liefert Statuswerte an Loxone zurück.</p>

  <h3>Wofür ist das Plugin gedacht?</h3>
  <ul>
    <li>PoE-Geräte über Loxone schalten, zum Beispiel Kameras, Access Points oder Gateways.</li>
    <li>Den aktuellen PoE-Status, die Leistung pro Port und die Online-Erreichbarkeit eines Switches abfragen.</li>
    <li>Fertige Loxone-Vorlagen erzeugen, damit virtuelle Ausgänge und HTTP-Eingänge nicht manuell gebaut werden müssen.</li>
  </ul>
  <p>Nicht gedacht ist die Bridge als vollständige UniFi-Verwaltung. Sie stellt gezielt die Funktionen bereit, die Loxone für PoE-Schalten und Statuswerte braucht.</p>

  <h3>Voraussetzungen</h3>
  <ul>
    <li>LoxBerry im gleichen Netzwerk wie der UniFi Controller oder die UDM.</li>
    <li>Mindestens ein adoptierter UniFi-Switch mit PoE-Ports.</li>
    <li>Ein lokaler UniFi-Benutzer mit Zugriff auf die Network-App. Kein Cloud-only Account.</li>
    <li>Ein freier Bridge-Port auf dem LoxBerry, standardmäßig <code>5000</code>.</li>
  </ul>

  <h3>Einrichtung in Reihenfolge</h3>
  <ol>
    <li>In der Konfiguration den UniFi-Host eintragen, zum Beispiel <code>https://192.168.1.1</code>.</li>
    <li>Site, lokalen UniFi-Benutzer und Passwort eintragen.</li>
    <li>API-Benutzer und API-Passwort für Loxone setzen. Das schützt die Bridge-Endpunkte im LAN.</li>
    <li><strong>Speichern &amp; Bridge neu starten</strong> klicken.</li>
    <li>Wenn der Status grün ist, <strong>Switches suchen</strong> verwenden und die gefundenen Switches speichern.</li>
    <li><strong>Loxone-Vorlagen herunterladen</strong> und die XML-Dateien in Loxone Config importieren.</li>
  </ol>

  <h3>Konfigurationsfelder</h3>
  <table>
    <thead><tr><th>Feld</th><th>Bedeutung</th></tr></thead>
    <tbody>
      <tr><td>Host</td><td>Adresse der UDM oder des UniFi Controllers inklusive Protokoll, meist <code>https://...</code>.</td></tr>
      <tr><td>Site</td><td>UniFi-Site. In den meisten Installationen ist das <code>default</code>.</td></tr>
      <tr><td>Benutzer / Passwort</td><td>Lokaler UniFi-Zugang, den die Bridge für die Network-API verwendet.</td></tr>
      <tr><td>API-Benutzer / API-Passwort</td><td>Zugangsdaten, die Loxone beim Aufruf der Bridge verwendet.</td></tr>
      <tr><td>Bridge-Port</td><td>HTTP-Port des Dienstes auf dem LoxBerry. Ändern, wenn <code>5000</code> bereits belegt ist.</td></tr>
      <tr><td>Switch-Name</td><td>Frei wählbarer Name für Loxone-Befehle, zum Beispiel <code>Rack</code>.</td></tr>
      <tr><td>MAC-Adresse</td><td>MAC des UniFi-Switches im Format <code>aa:bb:cc:dd:ee:ff</code>.</td></tr>
    </tbody>
  </table>

  <h3>Loxone verwenden</h3>
  <p>Am einfachsten ist der Weg über die generierten Vorlagen. Sie enthalten einen virtuellen Ausgang zum Schalten und virtuelle HTTP-Eingänge für Status, Leistung und Online-Zustand.</p>
  <p>Beispiel für einen manuellen Schaltaufruf:</p>
  <pre>http://LOXBERRY:5000/poe/set?switch=Rack&amp;ports=1,2&amp;state=off</pre>
  <p>Wenn API-Zugangsdaten gesetzt sind, muss Loxone Basic Auth mit dem konfigurierten API-Benutzer und API-Passwort senden.</p>

  <h3>Fehlersuche</h3>
  <table>
    <thead><tr><th>Problem</th><th>Prüfen</th></tr></thead>
    <tbody>
      <tr><td>Bridge nicht erreichbar</td><td>Port frei? Dienst neu gestartet? LoxBerry-Log des Plugins prüfen.</td></tr>
      <tr><td>UDM nicht erreichbar</td><td>Host-Adresse, HTTPS, Firewall und Zertifikatswarnungen prüfen.</td></tr>
      <tr><td>Login fehlgeschlagen</td><td>Lokalen UniFi-Benutzer, Passwort und Site prüfen.</td></tr>
      <tr><td>Switch wird nicht gefunden</td><td>Adoption in UniFi, MAC-Adresse und Online-Status des Switches prüfen.</td></tr>
      <tr><td>Loxone schaltet nicht</td><td>API-Benutzer/API-Passwort, Switch-Name und Portnummer im Befehl prüfen.</td></tr>
    </tbody>
  </table>

  <div class="ucb-note">
    <strong>Sicherheit:</strong> Die Bridge gehört nur ins lokale Netzwerk. API-Zugangsdaten sind Pflicht. Lege für UniFi einen eigenen Benutzer mit möglichst wenig Rechten an und lasse die Zertifikatsprüfung aktiv. Bei einem selbstsignierten Controller-Zertifikat kannst du eine eigene CA-Datei hinterlegen.
  </div>
</div>
<?php
if (class_exists('LBWeb')) {
    LBWeb::lbfooter();
}
?>
