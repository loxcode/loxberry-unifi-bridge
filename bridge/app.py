#!/usr/bin/env python3
# loxcode bridge - UniFi-PoE-Gateway für Loxone
# Copyright (C) 2026 loxcode
# Lizenz: GNU General Public License v3.0 - siehe LICENSE im Projekt-Root.
# Dieses Programm ist Freie Software ohne jegliche Gewährleistung.
"""loxcode bridge - UniFi-PoE-Gateway für Loxone.

HTTP-API kompatibel zur unifi-poe-bridge, plus Loxone-freundliche
.txt-Endpoints. Konfiguration via Env oder BRIDGE_CONFIG-JSON.
"""
import json
import hmac
import os
import re
from functools import wraps

from flask import Flask, Response, jsonify, request

from unifi_client import UnifiClient
import loxone_templates

ENV_KEYS = ("UNIFI_HOST", "UNIFI_SITE", "UNIFI_USER", "UNIFI_PASS",
            "DEFAULT_TIMEOUT", "API_USER", "API_PASS", "SWITCHES_JSON",
            "BRIDGE_PORT", "BRIDGE_BIND", "UNIFI_TLS_VERIFY",
            "UNIFI_CA_BUNDLE", "DEVICE_CACHE_TTL")

DEFAULTS = {"UNIFI_HOST": "https://192.168.1.1", "UNIFI_SITE": "default",
            "UNIFI_USER": "", "UNIFI_PASS": "", "DEFAULT_TIMEOUT": "5.0",
            "API_USER": "", "API_PASS": "", "SWITCHES_JSON": "{}",
            "BRIDGE_PORT": "5000", "BRIDGE_BIND": "0.0.0.0",
            "UNIFI_TLS_VERIFY": "true", "UNIFI_CA_BUNDLE": "",
            "DEVICE_CACHE_TTL": "2.0"}

APP_VERSION = "1.0.19"


def as_bool(value) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on", "ja")


def bounded_number(value, default, minimum, maximum, cast=float):
    try:
        parsed = cast(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def valid_bridge_host(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.:-]{0,252}", value or ""))


def secure_equal(left, right) -> bool:
    return hmac.compare_digest(
        str(left or "").encode("utf-8"), str(right or "").encode("utf-8"))


def load_settings() -> dict:
    settings = {k: os.getenv(k, DEFAULTS[k]) for k in ENV_KEYS}
    cfg_path = os.getenv("BRIDGE_CONFIG", "")
    if cfg_path and os.path.exists(cfg_path):
        try:
            with open(cfg_path, encoding="utf-8") as f:
                file_cfg = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("Bridge-Konfiguration ist nicht lesbar") from exc
        if not isinstance(file_cfg, dict):
            raise RuntimeError("Bridge-Konfiguration muss ein JSON-Objekt sein")
        for k in ENV_KEYS:
            if k in file_cfg:
                settings[k] = (json.dumps(file_cfg[k])
                               if isinstance(file_cfg[k], dict)
                               else str(file_cfg[k]))
        # Bestehende Installationen nutzten bisher immer verify=False. Nur neue
        # Standard-Configs aktivieren die Zertifikatsprüfung automatisch.
        if "UNIFI_TLS_VERIFY" not in file_cfg:
            settings["UNIFI_TLS_VERIFY"] = "false"
    return settings


def create_app(client, switches, api_user="", api_pass="", bridge_port=5000):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
    auth_configured = bool(api_user and api_pass)

    def require_auth(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not auth_configured:
                return jsonify({
                    "ok": False,
                    "error": "API-Zugangsdaten müssen zuerst konfiguriert werden",
                }), 503
            auth = request.authorization
            if (not auth
                    or not secure_equal(auth.username, api_user)
                    or not secure_equal(auth.password, api_pass)):
                return Response("Authentifizierung erforderlich", 401,
                                {"WWW-Authenticate": 'Basic realm="Login"'})
            return f(*args, **kwargs)
        return wrapper

    def resolve_switch():
        name = request.args.get("switch", "")
        if not switches:
            return None, (jsonify({"ok": False,
                                   "error": "keine Switches konfiguriert"}),
                          500)
        if name not in switches:
            return None, (jsonify({"ok": False,
                                   "error": "unbekannter switch-name"}), 400)
        return switches[name], None

    def parse_ports():
        ports = []
        for part in request.args.get("ports", "").split(","):
            part = part.strip()
            if not part:
                continue
            try:
                port = int(part)
                if port < 1 or port > 1024:
                    return None
                if port not in ports:
                    ports.append(port)
            except ValueError:
                return None
            if len(ports) > 128:
                return None
        return ports

    def txt(body: str):
        return Response(body, mimetype="text/plain")

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "unifi_bridge",
                        "version": APP_VERSION,
                        "auth_configured": auth_configured})

    @app.route("/selftest")
    @require_auth
    def selftest():
        # Read-only-Diagnose: prüft die Kette Bridge->UDM, ohne Zugangsdaten
        # oder MAC-Adressen preiszugeben.
        try:
            devices = client.get_devices()
        except Exception as e:  # noqa: BLE001 - Diagnose soll nie crashen
            return jsonify({"unifi_reachable": False, "login_ok": False,
                            "error": type(e).__name__,
                            "hint": "UNIFI_HOST/Netzwerk prüfen"}), 200
        login_ok = bool(devices)
        found_macs = {d.get("mac", "").lower() for d in devices}
        matched, missing = [], []
        for name, mac in switches.items():
            (matched if mac.lower() in found_macs else missing).append(name)
        return jsonify({
            "unifi_reachable": True,
            "login_ok": login_ok,
            "devices_in_controller": len(devices),
            "switches_configured": len(switches),
            "switches_found": matched,
            "switches_missing": missing,
            "hint": ("alles ok" if login_ok and not missing
                     else "keine Geräte - Login/Host prüfen" if not login_ok
                     else "einige Switches nicht gefunden - MAC/Adoption prüfen"),
        }), 200

    @app.route("/devices")
    @require_auth
    def devices():
        # Autoerkennung: alle PoE-Switches im Controller (fürs Webfrontend).
        try:
            found = client.discover_switches()
        except Exception as e:  # noqa: BLE001
            return jsonify({"ok": False, "error": type(e).__name__}), 200
        return jsonify({"ok": True, "switches": found})

    @app.route("/templates.zip")
    @require_auth
    def templates_zip():
        # Loxone-Vorlagen für die konfigurierten Switches als ZIP.
        # Ports werden per Discovery ermittelt; Host aus ?host= (Default:
        # der Host, über den der Aufruf kam).
        host = request.args.get("host") or request.host.split(":")[0]
        if not valid_bridge_host(host):
            return jsonify({"ok": False, "error": "ungültiger Bridge-Host"}), 400
        try:
            found = {s["mac"]: s for s in client.discover_switches()}
        except Exception:  # noqa: BLE001
            return jsonify({"ok": False,
                            "error": "Controller nicht erreichbar"}), 502
        tpl_switches, missing = [], []
        for name, mac in switches.items():
            sw = found.get(mac.lower())
            if not sw or not sw["poe_ports"]:
                missing.append(name)
                continue
            tpl_switches.append({"name": name, "mac": mac,
                                 "ports": sw["poe_ports"]})
        if missing:
            return jsonify({"ok": False,
                            "error": "Switch(es) nicht im Controller gefunden: "
                                     + ", ".join(missing)}), 409
        if not tpl_switches:
            return jsonify({"ok": False,
                            "error": "keine Switches konfiguriert"}), 409
        cfg = {"bridge_host": host, "bridge_port": bridge_port,
               "api_user": api_user, "api_pass": api_pass}
        data = loxone_templates.build_zip_bytes(cfg, tpl_switches)
        return Response(
            data, mimetype="application/zip",
            headers={"Content-Disposition":
                     "attachment; filename=loxcode-bridge-loxone-vorlagen.zip"})

    @app.route("/poe/set")
    @require_auth
    def poe_set():
        mac, err = resolve_switch()
        if err:
            return err
        ports = parse_ports()
        if not ports:
            return jsonify({"ok": False,
                            "error": "keine/ungültige ports"}), 400
        state = (request.args.get("state") or "").lower()
        if state not in ("on", "off"):
            return jsonify({"ok": False,
                            "error": "state muss 'on' oder 'off' sein"}), 400
        ok, msg = client.set_poe(mac, ports, state)
        return jsonify({"ok": ok, "message": msg}), (200 if ok else 500)

    def _status_data():
        mac, err = resolve_switch()
        if err:
            return None, err
        ports = parse_ports()
        if not ports:
            return None, (jsonify({"ok": False,
                                   "error": "keine/ungültige ports"}), 400)
        data = client.poe_status(mac, ports)
        if data is None:
            return None, (jsonify({"ok": False,
                                   "error": "Switch nicht gefunden"}), 500)
        return data, None

    @app.route("/poe/status")
    @require_auth
    def poe_status():
        data, err = _status_data()
        if err:
            return err
        result = {"ok": True,
                  "ports": {str(k): v for k, v in data.items()}}
        states = set(data.values())
        if states == {"on"}:
            result["all"] = "on"
        elif states == {"off"}:
            result["all"] = "off"
        return jsonify(result)

    @app.route("/poe/status.txt")
    @require_auth
    def poe_status_txt():
        data, err = _status_data()
        if err:
            return err
        num = {"on": "1", "off": "0", "unknown": "-1"}
        parts = [f"port{i}={num[data[i]]}" for i in sorted(data)]
        vals = set(data.values())
        if vals == {"on"}:
            parts.append("all=1")
        elif vals == {"off"}:
            parts.append("all=0")
        return txt(";".join(parts))

    def _power_data():
        mac, err = resolve_switch()
        if err:
            return None, err
        ports = parse_ports()
        if not ports:
            return None, (jsonify({"ok": False,
                                   "error": "keine/ungültige ports"}), 400)
        data = client.poe_power(mac, ports)
        if data is None:
            return None, (jsonify({"ok": False,
                                   "error": "Switch nicht gefunden"}), 500)
        return data, None

    @app.route("/poe/power")
    @require_auth
    def poe_power():
        data, err = _power_data()
        if err:
            return err
        return jsonify({"ok": True,
                        "ports": {str(k): v for k, v in data.items()}})

    @app.route("/poe/power.txt")
    @require_auth
    def poe_power_txt():
        data, err = _power_data()
        if err:
            return err
        return txt(";".join(f"port{i}={data[i]:.1f}" for i in sorted(data)))

    @app.route("/device/status")
    @require_auth
    def device_status():
        mac, err = resolve_switch()
        if err:
            return err
        online = client.device_online(mac)
        if online is None:
            return jsonify({"ok": False,
                            "error": "Switch nicht gefunden"}), 500
        return jsonify({"ok": True, "online": bool(online)})

    @app.route("/device/status.txt")
    @require_auth
    def device_status_txt():
        mac, err = resolve_switch()
        if err:
            return err
        online = client.device_online(mac)
        if online is None:
            return jsonify({"ok": False,
                            "error": "Switch nicht gefunden"}), 500
        return txt(f"online={1 if online else 0}")

    return app


def create_runtime_app():
    s = load_settings()
    try:
        switches = json.loads(s["SWITCHES_JSON"])
    except json.JSONDecodeError:
        switches = {}
    timeout = bounded_number(s["DEFAULT_TIMEOUT"], 5.0, 0.5, 60.0)
    cache_ttl = bounded_number(s["DEVICE_CACHE_TTL"], 2.0, 0.0, 30.0)
    verify = s["UNIFI_CA_BUNDLE"].strip() or as_bool(s["UNIFI_TLS_VERIFY"])
    client = UnifiClient(
        s["UNIFI_HOST"],
        site=s["UNIFI_SITE"],
        username=s["UNIFI_USER"],
        password=s["UNIFI_PASS"],
        timeout=timeout,
        verify=verify,
        device_cache_ttl=cache_ttl,
    )
    port = bounded_number(s["BRIDGE_PORT"], 5000, 1, 65535, int)
    return create_app(client, switches,
                      api_user=s["API_USER"], api_pass=s["API_PASS"],
                      bridge_port=port)


application = create_runtime_app()


def main():
    s = load_settings()
    port = bounded_number(s["BRIDGE_PORT"], 5000, 1, 65535, int)
    bind = s["BRIDGE_BIND"] if valid_bridge_host(s["BRIDGE_BIND"]) else "0.0.0.0"
    application.run(host=bind, port=port, threaded=True)


if __name__ == "__main__":
    main()
