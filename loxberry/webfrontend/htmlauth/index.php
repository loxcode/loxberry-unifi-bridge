<?php
// UniFi Bridge (LOXCODE) - Konfigurationsseite
// Kein jQuery Mobile (lbheader mit 4. Parameter=true) -> normales HTML.
@include_once "loxberry_system.php";
@include_once "loxberry_web.php";

if (PHP_SAPI !== 'cli' && session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}
if (!isset($_SESSION['unifi_bridge_csrf'])) {
    $_SESSION['unifi_bridge_csrf'] = bin2hex(random_bytes(32));
}
$csrf_token = $_SESSION['unifi_bridge_csrf'];

// Echten Plugin-Ordnernamen ermitteln (LoxBerry kann Suffixe anhängen)
$plugindir = basename(__DIR__);
$configdir = isset($lbpconfigdir) ? $lbpconfigdir
    : "/opt/loxberry/config/plugins/" . $plugindir;
$bindir = isset($lbpbindir) ? $lbpbindir
    : "/opt/loxberry/bin/plugins/" . $plugindir;
$configfile = $configdir . "/config.json";
$msg = '';
$msg_ok = true;
$MAX_SWITCHES = 8;
$discovered = null;   // Ergebnis der Switch-Autoerkennung

$rawcfg = file_exists($configfile)
    ? json_decode(file_get_contents($configfile), true)
    : array();
$legacy_tls_config = is_array($rawcfg) && !array_key_exists('UNIFI_TLS_VERIFY', $rawcfg);
$defaults = array('UNIFI_HOST' => 'https://192.168.1.1', 'UNIFI_SITE' => 'default',
    'UNIFI_USER' => '', 'UNIFI_PASS' => '', 'DEFAULT_TIMEOUT' => '5.0',
    'API_USER' => '', 'API_PASS' => '', 'SWITCHES_JSON' => '{}',
    'BRIDGE_PORT' => '5000', 'BRIDGE_BIND' => '0.0.0.0',
    'UNIFI_TLS_VERIFY' => 'true', 'UNIFI_CA_BUNDLE' => '',
    'DEVICE_CACHE_TTL' => '2.0');
$plugincfg = array_merge($defaults, is_array($rawcfg) ? $rawcfg : array());
if ($legacy_tls_config) { $plugincfg['UNIFI_TLS_VERIFY'] = 'false'; }
$SECRETS = array('UNIFI_PASS', 'API_PASS');

function h($value) {
    return htmlspecialchars((string)$value, ENT_QUOTES, 'UTF-8');
}

function atomic_write_json($path, $value) {
    $dir = dirname($path);
    $tmp = tempnam($dir, '.config.');
    if ($tmp === false) { return false; }
    $json = json_encode($value, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    $written = @file_put_contents($tmp, $json . "\n", LOCK_EX);
    if ($written === false || !@chmod($tmp, 0600) || !@rename($tmp, $path)) {
        @unlink($tmp);
        return false;
    }
    return $written;
}

function valid_unifi_host($value) {
    $parts = @parse_url($value);
    return is_array($parts)
        && isset($parts['scheme'], $parts['host'])
        && in_array(strtolower($parts['scheme']), array('http', 'https'), true)
        && !isset($parts['user']) && !isset($parts['pass']) && !isset($parts['query']);
}

// Ruft die lokale Bridge auf (mit Basic Auth aus der Config). $code per Referenz.
function bridge_call($path, &$code, &$ctype) {
    global $plugincfg;
    $url = 'http://127.0.0.1:' . $plugincfg['BRIDGE_PORT'] . $path;
    $hdr = array();
    if ($plugincfg['API_USER'] !== '' && $plugincfg['API_PASS'] !== '') {
        $hdr[] = 'Authorization: Basic '
               . base64_encode($plugincfg['API_USER'] . ':' . $plugincfg['API_PASS']);
    }
    $ctx = stream_context_create(array('http' => array(
        'header' => implode("\r\n", $hdr), 'timeout' => 20, 'ignore_errors' => true)));
    $body = @file_get_contents($url, false, $ctx);
    $code = 0; $ctype = '';
    if (isset($http_response_header)) {
        foreach ($http_response_header as $h) {
            if (preg_match('#^HTTP/\S+\s+(\d{3})#', $h, $mm)) { $code = intval($mm[1]); }
            if (stripos($h, 'Content-Type:') === 0) { $ctype = trim(substr($h, 13)); }
        }
    }
    return $body;
}

$action = isset($_POST['action']) ? $_POST['action'] : 'save';

if ($_SERVER['REQUEST_METHOD'] === 'POST' && PHP_SAPI !== 'cli') {
    $posted_csrf = isset($_POST['csrf_token']) ? (string)$_POST['csrf_token'] : '';
    if (!hash_equals($csrf_token, $posted_csrf)) {
        http_response_code(403);
        exit('Ungültige Anfrage. Bitte die Pluginseite neu laden.');
    }
}

// --- Aktion: Vorlagen-Download (muss VOR jeglicher Ausgabe passieren) --------
if ($_SERVER['REQUEST_METHOD'] === 'POST' && $action === 'download') {
    $host = preg_replace('/:\d+$/', '', $_SERVER['HTTP_HOST']);
    $code = 0; $ctype = '';
    $zip = bridge_call('/templates.zip?host=' . urlencode($host), $code, $ctype);
    if ($code === 200 && $zip !== false && strlen($zip) > 0) {
        header('Content-Type: application/zip');
        header('Content-Disposition: attachment; filename=loxcode-bridge-loxone-vorlagen.zip');
        header('Content-Length: ' . strlen($zip));
        echo $zip;
        exit;
    }
    $err = json_decode((string)$zip, true);
    $msg = 'Vorlagen konnten nicht erzeugt werden'
         . (is_array($err) && isset($err['error']) ? ': ' . $err['error'] : ' (Bridge/Verbindung prüfen).');
    $msg_ok = false;
}

// --- Aktion: Speichern -------------------------------------------------------
if ($_SERVER['REQUEST_METHOD'] === 'POST' && $action === 'save') {
    foreach (array('UNIFI_HOST', 'UNIFI_SITE', 'UNIFI_USER',
                   'DEFAULT_TIMEOUT', 'API_USER', 'BRIDGE_PORT',
                   'BRIDGE_BIND', 'UNIFI_TLS_VERIFY', 'UNIFI_CA_BUNDLE',
                   'DEVICE_CACHE_TTL') as $k) {
        if (isset($_POST[$k])) { $plugincfg[$k] = trim($_POST[$k]); }
    }
    foreach ($SECRETS as $k) {
        if (!empty($_POST['clear_' . $k])) {
            $plugincfg[$k] = '';
        } elseif (isset($_POST[$k]) && $_POST[$k] !== '') {
            $plugincfg[$k] = trim($_POST[$k]);
        }
    }
    $port = filter_var($plugincfg['BRIDGE_PORT'], FILTER_VALIDATE_INT,
        array('options' => array('min_range' => 1, 'max_range' => 65535)));
    $timeout = filter_var($plugincfg['DEFAULT_TIMEOUT'], FILTER_VALIDATE_FLOAT);
    $cache_ttl = filter_var($plugincfg['DEVICE_CACHE_TTL'], FILTER_VALIDATE_FLOAT);
    if (!valid_unifi_host($plugincfg['UNIFI_HOST'])) {
        $msg = 'UniFi-Host muss eine vollständige HTTP- oder HTTPS-URL ohne Zugangsdaten sein.';
        $msg_ok = false;
    } elseif (!preg_match('/^[A-Za-z0-9._-]{1,64}$/', $plugincfg['UNIFI_SITE'])) {
        $msg = 'Die UniFi-Site enthält ungültige Zeichen.';
        $msg_ok = false;
    } elseif ($port === false) {
        $msg = 'Der Bridge-Port muss zwischen 1 und 65535 liegen.';
        $msg_ok = false;
    } elseif ($timeout === false || $timeout < 0.5 || $timeout > 60) {
        $msg = 'Der Timeout muss zwischen 0,5 und 60 Sekunden liegen.';
        $msg_ok = false;
    } elseif ($cache_ttl === false || $cache_ttl < 0 || $cache_ttl > 30) {
        $msg = 'Der Gerätecache muss zwischen 0 und 30 Sekunden liegen.';
        $msg_ok = false;
    } elseif (!in_array($plugincfg['BRIDGE_BIND'], array('0.0.0.0', '127.0.0.1'), true)) {
        $msg = 'Die Bind-Adresse muss 0.0.0.0 oder 127.0.0.1 sein.';
        $msg_ok = false;
    } elseif ($plugincfg['UNIFI_CA_BUNDLE'] !== ''
            && (!is_file($plugincfg['UNIFI_CA_BUNDLE']) || !is_readable($plugincfg['UNIFI_CA_BUNDLE']))) {
        $msg = 'Die angegebene CA-Datei existiert nicht oder ist nicht lesbar.';
        $msg_ok = false;
    } elseif ($plugincfg['API_USER'] === '' || $plugincfg['API_PASS'] === '') {
        $msg = 'API-Benutzer und API-Passwort sind Pflicht, weil die Bridge PoE-Ports schalten kann.';
        $msg_ok = false;
    }
    if ($port !== false) { $plugincfg['BRIDGE_PORT'] = (string)$port; }
    if ($timeout !== false) { $plugincfg['DEFAULT_TIMEOUT'] = (string)$timeout; }
    if ($cache_ttl !== false) { $plugincfg['DEVICE_CACHE_TTL'] = (string)$cache_ttl; }
    $sw = array();
    for ($i = 0; $i < $MAX_SWITCHES; $i++) {
        $n = isset($_POST["sw_name_$i"]) ? trim($_POST["sw_name_$i"]) : '';
        $m = isset($_POST["sw_mac_$i"]) ? strtolower(trim($_POST["sw_mac_$i"])) : '';
        if ($n === '' && $m === '') { continue; }
        if ($n === '' || strlen($n) > 64 || preg_match('/[\x00-\x1F\x7F]/', $n)
                || !preg_match('/^([0-9a-f]{2}:){5}[0-9a-f]{2}$/', $m)) {
            $msg = "Zeile " . ($i + 1) . ": Name fehlt oder MAC ungültig "
                 . "(Format aa:bb:cc:dd:ee:ff) - nicht gespeichert.";
            $msg_ok = false;
            break;
        }
        $sw[$n] = $m;
    }
    if ($msg_ok) {
        $plugincfg['SWITCHES_JSON'] = json_encode($sw, JSON_UNESCAPED_SLASHES);
        if (!is_dir($configdir)) { @mkdir($configdir, 0750, true); }
        $written = atomic_write_json($configfile, $plugincfg);
        if ($written === false) {
            $msg = 'Konnte ' . $configfile . ' nicht schreiben (Rechte?).';
            $msg_ok = false;
        } else {
            exec('bash ' . escapeshellarg($bindir . '/restart.sh') . ' 2>&1', $out, $rc);
            sleep(1);
            $msg = ($rc === 0) ? 'Gespeichert - Bridge wurde neu gestartet.'
                 : 'Gespeichert, aber Neustart fehlgeschlagen: ' . implode(' | ', $out);
            $msg_ok = ($rc === 0);
        }
    }
}

// --- Aktion: Switch-Autoerkennung -------------------------------------------
if ($_SERVER['REQUEST_METHOD'] === 'POST' && $action === 'discover') {
    $code = 0; $ctype = '';
    $resp = json_decode((string)bridge_call('/devices', $code, $ctype), true);
    if ($code === 200 && is_array($resp) && !empty($resp['ok'])) {
        $discovered = $resp['switches'];
        if (!$discovered) {
            $msg = 'Keine PoE-Switches im Controller gefunden.';
            $msg_ok = false;
        }
    } else {
        $msg = 'Erkennung fehlgeschlagen - zuerst UniFi-Zugang speichern und '
             . 'prüfen (Bridge muss laufen).';
        $msg_ok = false;
    }
}

// Aktuelle Switch-Zeilen (nach Erkennung: gefundene Switches vorbelegen)
$switches = json_decode($plugincfg['SWITCHES_JSON'], true);
if (!is_array($switches)) { $switches = array(); }
$sw_rows = array();
if (is_array($discovered)) {
    foreach ($discovered as $d) { $sw_rows[] = array($d['name'], $d['mac']); }
} else {
    foreach ($switches as $n => $m) { $sw_rows[] = array($n, $m); }
}

$base = 'http://127.0.0.1:' . $plugincfg['BRIDGE_PORT'];
$health = @file_get_contents($base . '/health');
$health_data = ($health !== false) ? json_decode($health, true) : null;
$running = (is_array($health_data)
    && isset($health_data['status'], $health_data['service'], $health_data['version'])
    && $health_data['status'] === 'ok'
    && $health_data['service'] === 'unifi_bridge'
    && $health_data['version'] === '1.0.19');
$health_mismatch = ($health !== false && !$running);
$selftest = null;
if ($running && $plugincfg['API_USER'] !== '' && $plugincfg['API_PASS'] !== '') {
    $selftest_code = 0; $selftest_type = '';
    $selftest = json_decode((string)bridge_call('/selftest', $selftest_code, $selftest_type), true);
}
$has_switches = (count($switches) > 0);

function tf($label, $name, $value, $type = 'text', $ph = '') {
    $extra = '';
    if ($type === 'password') {
        $has = ($value !== '');
        $value = '';
        $ph = $has ? 'gespeichert - zum Ändern neu eingeben' : 'nicht gesetzt';
        $extra = ' autocomplete="new-password"';
    }
    echo '<tr><td style="padding:4px 10px 4px 0;white-space:nowrap;">'
       . $label . '</td><td style="padding:4px 0;">'
       . '<input type="' . $type . '" name="' . $name . '" style="width:320px;"'
       . $extra . ' value="' . h($value) . '"'
       . ($ph ? ' placeholder="' . h($ph) . '"' : '') . '></td></tr>' . "\n";
}

// 4. Parameter true => jQuery Mobile wird NICHT geladen
if (class_exists('LBWeb')) {
    LBWeb::lbheader("UniFi Bridge", "https://github.com/loxcode", "", true);
}
?>
<div style="max-width:780px;margin:0 auto;padding:10px;">
<h2 style="margin-bottom:2px;">UniFi Bridge <small style="font-weight:normal;color:#666;">by LOXCODE</small></h2>
<p style="margin-top:0;">PoE-Ports schalten &amp; Status f&uuml;r Loxone &mdash; via UniFi-Controller/UDM.</p>
<p style="margin-top:0;"><a href="help.php" style="display:inline-block;border:1px solid #9aa6b2;border-radius:4px;background:#fff;color:#111;text-decoration:none;padding:7px 12px;font-weight:bold;">Hilfe &amp; Anleitung</a></p>

<p>Bridge-Status:
<?php echo $running
    ? '<strong style="color:#2e7d32;">&#9679; l&auml;uft</strong>'
    : '<strong style="color:#c62828;">&#9679; nicht erreichbar</strong>'; ?>
</p>
<?php if ($health_mismatch) { ?>
  <p style="border:1px solid #c62828;color:#c62828;padding:8px 12px;border-radius:4px;">
    Auf dem konfigurierten Port antwortet ein anderer Dienst oder eine alte Bridge-Version.
  </p>
<?php } ?>
<?php if ($plugincfg['API_USER'] === '' || $plugincfg['API_PASS'] === '') { ?>
  <p style="border:1px solid #c62828;color:#c62828;padding:8px 12px;border-radius:4px;">
    Die Bridge-Endpunkte sind gesperrt. Bitte API-Benutzer und API-Passwort konfigurieren.
  </p>
<?php } ?>

<?php if (is_array($selftest)) {
    $ok = !empty($selftest['login_ok']) && empty($selftest['switches_missing']);
    $c = $ok ? '#2e7d32' : '#e65100';
    echo '<div style="border:1px solid ' . $c . ';border-radius:4px;padding:8px 12px;margin-bottom:8px;">';
    echo '<strong>Verbindungstest UDM:</strong> ';
    if (empty($selftest['unifi_reachable'])) {
        echo '<span style="color:#c62828;">UDM nicht erreichbar</span> &ndash; UNIFI_HOST / Netzwerk pr&uuml;fen.';
    } elseif (empty($selftest['login_ok'])) {
        echo '<span style="color:#c62828;">Login fehlgeschlagen</span> &ndash; Benutzer/Passwort/Site pr&uuml;fen.';
    } else {
        echo '<span style="color:#2e7d32;">Login OK</span>, '
           . intval($selftest['devices_in_controller']) . ' Ger&auml;t(e) im Controller. ';
        $found = $selftest['switches_found'] ? implode(', ', array_map('htmlspecialchars', $selftest['switches_found'])) : '&ndash;';
        echo 'Gefundene Switches: <strong>' . $found . '</strong>.';
        if (!empty($selftest['switches_missing'])) {
            echo ' <span style="color:#e65100;">Nicht gefunden: '
               . implode(', ', array_map('htmlspecialchars', $selftest['switches_missing']))
               . '</span> (MAC / Adoption pr&uuml;fen).';
        }
    }
    echo '</div>';
} ?>

<?php if ($msg) {
    $c = $msg_ok ? '#2e7d32' : '#c62828';
    echo '<p style="border:1px solid ' . $c . ';color:' . $c
       . ';padding:8px 12px;border-radius:4px;background:#f7f7f7;">'
       . htmlspecialchars($msg) . '</p>';
} ?>

<?php if (is_array($discovered) && $discovered) { ?>
<div style="border:1px solid #2e7d32;border-radius:4px;padding:8px 12px;margin-bottom:10px;">
<strong><?php echo count($discovered); ?> Switch(es) gefunden</strong> &ndash; unten pr&uuml;fen und speichern:
<ul style="margin:6px 0;">
<?php foreach ($discovered as $d) {
    $power = 0.0; foreach ($d['poe_power'] as $w) { $power += $w; }
    echo '<li>' . htmlspecialchars($d['name']) . ' <small>('
       . htmlspecialchars($d['model']) . ', ' . htmlspecialchars($d['mac']) . ')</small> '
       . '&ndash; PoE-Ports ' . htmlspecialchars(implode(',', $d['poe_ports']))
       . ' &middot; ' . number_format($power, 1) . ' W'
       . (empty($d['online']) ? ' <span style="color:#c62828;">offline</span>' : '')
       . '</li>';
} ?>
</ul>
</div>
<?php } ?>

<form method="post" action="index.php">
  <input type="hidden" name="csrf_token" value="<?php echo h($csrf_token); ?>">
  <input type="hidden" name="action" value="save">

  <h3>UniFi-Controller / UDM</h3>
  <table><tbody>
  <?php
  tf('Host (URL)', 'UNIFI_HOST', $plugincfg['UNIFI_HOST'], 'text', 'https://192.168.1.1');
  tf('Site', 'UNIFI_SITE', $plugincfg['UNIFI_SITE']);
  tf('Benutzer (lokaler UniFi-User)', 'UNIFI_USER', $plugincfg['UNIFI_USER']);
  tf('Passwort', 'UNIFI_PASS', $plugincfg['UNIFI_PASS'], 'password');
  tf('Timeout (Sekunden)', 'DEFAULT_TIMEOUT', $plugincfg['DEFAULT_TIMEOUT']);
  ?>
  </tbody></table>
  <label><input type="checkbox" name="clear_UNIFI_PASS" value="1"> gespeichertes UniFi-Passwort löschen</label>

  <h3>Controller-Zertifikat</h3>
  <table><tbody>
    <tr><td style="padding:4px 10px 4px 0;">TLS-Prüfung</td><td>
      <select name="UNIFI_TLS_VERIFY" style="width:320px;">
        <option value="true"<?php echo $plugincfg['UNIFI_TLS_VERIFY'] !== 'false' ? ' selected' : ''; ?>>Zertifikat prüfen</option>
        <option value="false"<?php echo $plugincfg['UNIFI_TLS_VERIFY'] === 'false' ? ' selected' : ''; ?>>Unsicher - Prüfung deaktivieren</option>
      </select>
    </td></tr>
  <?php tf('Eigene CA-Datei (optional)', 'UNIFI_CA_BUNDLE', $plugincfg['UNIFI_CA_BUNDLE'], 'text', '/pfad/ca.pem'); ?>
  </tbody></table>
  <?php if ($plugincfg['UNIFI_TLS_VERIFY'] === 'false') { ?>
    <p style="color:#c62828;"><strong>Warnung:</strong> Ohne Zertifikatsprüfung können UniFi-Zugangsdaten im Netzwerk abgefangen werden.</p>
  <?php } ?>

  <h3>Bridge-API (Zugang f&uuml;r Loxone)</h3>
  <table><tbody>
  <?php
  tf('API-Benutzer', 'API_USER', $plugincfg['API_USER']);
  tf('API-Passwort', 'API_PASS', $plugincfg['API_PASS'], 'password');
  tf('Bridge-Port', 'BRIDGE_PORT', $plugincfg['BRIDGE_PORT']);
  tf('Bind-Adresse', 'BRIDGE_BIND', $plugincfg['BRIDGE_BIND'], 'text', '0.0.0.0');
  tf('Gerätecache (Sekunden)', 'DEVICE_CACHE_TTL', $plugincfg['DEVICE_CACHE_TTL']);
  ?>
  </tbody></table>
  <p><small>API-Benutzer und API-Passwort sind Pflicht. Ohne beide Angaben bleiben alle Bridge-Endpunkte außer <code>/health</code> gesperrt.</small></p>

  <h3>Switches</h3>
  <p style="margin-top:0;"><small>Name frei w&auml;hlbar (wird in den Loxone-Befehlen verwendet),
  MAC im Format <code>aa:bb:cc:dd:ee:ff</code>. Mit <em>Switches suchen</em> automatisch f&uuml;llen.</small></p>
  <table><tbody>
  <tr><th style="text-align:left;padding-right:10px;">Name</th><th style="text-align:left;">MAC-Adresse</th></tr>
  <?php for ($i = 0; $i < $MAX_SWITCHES; $i++) {
      $n = isset($sw_rows[$i]) ? $sw_rows[$i][0] : '';
      $m = isset($sw_rows[$i]) ? $sw_rows[$i][1] : '';
  ?>
  <tr>
    <td style="padding:3px 10px 3px 0;"><input type="text" name="sw_name_<?php echo $i; ?>"
        style="width:200px;" value="<?php echo htmlspecialchars($n); ?>"
        placeholder="z. B. Rack-Switch"></td>
    <td style="padding:3px 0;"><input type="text" name="sw_mac_<?php echo $i; ?>"
        style="width:200px;" value="<?php echo htmlspecialchars($m); ?>"
        placeholder="aa:bb:cc:dd:ee:ff"></td>
  </tr>
  <?php } ?>
  </tbody></table>

  <p style="margin-top:16px;">
    <button type="submit" name="action" value="save" style="padding:8px 18px;font-size:15px;cursor:pointer;">
      Speichern &amp; Bridge neu starten</button>
    &nbsp;
    <button type="submit" name="action" value="discover" style="padding:8px 18px;font-size:15px;cursor:pointer;"
      <?php echo $running ? '' : 'disabled title="Bridge muss laufen"'; ?>>
      Switches suchen</button>
  </p>
</form>

<?php if ($running && $has_switches) { ?>
<form method="post" action="index.php" style="margin-top:4px;">
  <input type="hidden" name="csrf_token" value="<?php echo h($csrf_token); ?>">
  <input type="hidden" name="action" value="download">
  <h3>Loxone-Vorlagen</h3>
  <p style="margin-top:0;"><small>Erzeugt aus den gespeicherten Switches ein ZIP mit
  virtuellem Ausgang (PoE an/aus) und HTTP-Eing&auml;ngen (Status, Watt, Online) &mdash;
  in Loxone Config importieren.</small></p>
  <button type="submit" style="padding:8px 18px;font-size:15px;cursor:pointer;">
    Loxone-Vorlagen herunterladen (ZIP)</button>
</form>
<?php } ?>
</div>
<?php
if (class_exists('LBWeb')) {
    LBWeb::lbfooter();
}
?>
