#!/usr/bin/env python3
# loxcode bridge - Copyright (C) 2026 loxcode
# Lizenz: GNU General Public License v3.0 - siehe LICENSE im Projekt-Root.
"""UniFi-Session-API-Client (Login/Cookie/CSRF/Auto-Relogin).

Portiert aus der produktiv erprobten unifi-poe-bridge; probiert je
Aufruf den UniFi-OS-Proxypfad und den Legacy-Controllerpfad.
"""
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class UnifiClient:
    def __init__(self, host, site="default", username="", password="",
                 timeout=5.0):
        self.host = host.rstrip("/")
        self.site = site
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = requests.Session()
        self._logged_in = False

    # ---------- Auth ----------

    def login(self, force=False) -> bool:
        if self._logged_in and not force:
            return True
        payload = {"username": self.username, "password": self.password}
        for path in ("/api/auth/login", "/api/login"):
            try:
                r = self.session.post(self.host + path, json=payload,
                                      verify=False, timeout=self.timeout)
            except requests.RequestException:
                continue
            if r.status_code in (200, 201):
                csrf = (r.headers.get("X-CSRF-Token")
                        or r.headers.get("x-csrf-token"))
                if csrf:
                    self.session.headers["X-CSRF-Token"] = csrf
                self._logged_in = True
                return True
        self._logged_in = False
        return False

    def _request(self, method, path, **kwargs):
        if not self.login():
            return None
        try:
            r = self.session.request(method, self.host + path, verify=False,
                                     timeout=self.timeout, **kwargs)
        except requests.RequestException:
            return None
        if r.status_code == 401:
            if not self.login(force=True):
                return r
            try:
                r = self.session.request(method, self.host + path,
                                         verify=False, timeout=self.timeout,
                                         **kwargs)
            except requests.RequestException:
                return None
        return r

    def _api(self, method, subpath, **kwargs):
        r = None
        for prefix in (f"/proxy/network/api/s/{self.site}",
                       f"/api/s/{self.site}"):
            r = self._request(method, prefix + subpath, **kwargs)
            if r is not None and r.status_code == 200:
                return r
        return r

    # ---------- Geraete ----------

    def get_devices(self) -> list:
        r = self._api("GET", "/stat/device")
        if r is not None and r.status_code == 200:
            return r.json().get("data", [])
        return []

    def find_switch(self, mac):
        mac = mac.lower()
        for dev in self.get_devices():
            if dev.get("mac", "").lower() == mac:
                return dev
        return None

    def discover_switches(self) -> list:
        """Alle PoE-faehigen Switches im Controller finden (fuer die
        Autoerkennung im Webfrontend). Nur Geraete mit mind. einem
        PoE-Port (port_table-Eintrag mit poe_mode)."""
        out = []
        for dev in self.get_devices():
            poe_ports, power = [], {}
            for p in dev.get("port_table", []):
                if p.get("poe_mode") is None:
                    continue
                idx = p.get("port_idx")
                if idx is None:
                    continue
                poe_ports.append(idx)
                try:
                    power[idx] = float(p.get("poe_power"))
                except (TypeError, ValueError):
                    power[idx] = 0.0
            if not poe_ports:
                continue
            out.append({
                "name": dev.get("name", ""),
                "mac": dev.get("mac", "").lower(),
                "model": dev.get("model", ""),
                "online": dev.get("state") == 1,
                "poe_ports": sorted(poe_ports),
                "poe_power": power,
            })
        return out

    # ---------- PoE ----------

    def set_poe(self, mac, ports, state):
        if state not in ("on", "off"):
            raise ValueError("state muss 'on' oder 'off' sein")
        dev = self.find_switch(mac)
        if not dev:
            return False, "Switch mit dieser MAC nicht gefunden"
        overrides = dev.get("port_overrides", [])
        mode = "auto" if state == "on" else "off"
        for idx in ports:
            o = next((o for o in overrides if o.get("port_idx") == idx), None)
            if o:
                o["poe_mode"] = mode
                o["setting_preference"] = "manual"
            else:
                overrides.append({"port_idx": idx, "poe_mode": mode,
                                  "setting_preference": "manual"})
        r = self._api("PUT", f"/rest/device/{dev['_id']}",
                      json={"port_overrides": overrides})
        if r is None or r.status_code != 200:
            code = getattr(r, "status_code", "keine Antwort")
            return False, f"Update der port_overrides fehlgeschlagen: {code}"
        self._api("POST", "/cmd/devmgr",
                  json={"cmd": "force-provision", "mac": mac.lower()})
        return True, "OK"

    def poe_status(self, mac, ports):
        dev = self.find_switch(mac)
        if not dev:
            return None
        overrides = dev.get("port_overrides", [])
        table = dev.get("port_table", [])
        out = {}
        for idx in ports:
            mode = next((o.get("poe_mode") for o in overrides
                         if o.get("port_idx") == idx), None)
            if mode is None:
                mode = next((p.get("poe_mode") for p in table
                             if p.get("port_idx") == idx), None)
            if mode == "off":
                out[idx] = "off"
            elif mode in ("auto", "passthrough", "pasv24"):
                out[idx] = "on"
            else:
                out[idx] = "unknown"
        return out

    def poe_power(self, mac, ports):
        dev = self.find_switch(mac)
        if not dev:
            return None
        table = dev.get("port_table", [])
        out = {}
        for idx in ports:
            raw = next((p.get("poe_power") for p in table
                        if p.get("port_idx") == idx), None)
            try:
                out[idx] = float(raw)
            except (TypeError, ValueError):
                out[idx] = 0.0
        return out

    def device_online(self, mac):
        dev = self.find_switch(mac)
        if not dev:
            return None
        return dev.get("state") == 1
