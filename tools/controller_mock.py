#!/usr/bin/env python3
"""Simuliert die UniFi-Session-API (Login/Cookie/CSRF) fuer Tests.

Start als Server: python3 tools/controller_mock.py [port]
"""
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_RE_API = re.compile(r"^(?:/proxy/network)?/api/s/([^/]+)(/.*)$")


class ControllerState:
    def __init__(self):
        self.username = "bridge"
        self.password = "pw"
        self.csrf = "csrf-token-1"
        self.cookies = set()
        self.cookie_counter = 0
        self.session_max_requests = None
        self.request_count = 0
        self.login_count = 0
        self.puts = []
        self.provisions = []
        self.devices = [{
            "_id": "abc123",
            "mac": "aa:bb:cc:dd:ee:ff",
            "name": "Switch24",
            "model": "USW-24-PoE",
            "state": 1,
            "port_overrides": [],
            "port_table": [
                {"port_idx": 1, "poe_mode": "auto", "poe_power": "4.50"},
                {"port_idx": 2, "poe_mode": "off", "poe_power": "0.00"},
                {"port_idx": 3, "poe_mode": "auto", "poe_power": "2.10"},
            ],
        }]


class ControllerMock:
    def __init__(self, state=None):
        self.state = state or ControllerState()
        self._server = None
        self._thread = None

    # ---------- Kernlogik (auch ohne Server testbar) ----------

    def handle(self, method, path, headers, body):
        headers = {k.lower(): v for k, v in headers.items()}
        st = self.state

        if method == "POST" and path in ("/api/auth/login", "/api/login"):
            try:
                creds = json.loads(body.decode() or "{}")
            except json.JSONDecodeError:
                return 400, {}, {"error": "invalid json"}
            if (creds.get("username") == st.username
                    and creds.get("password") == st.password):
                st.cookie_counter += 1
                st.login_count += 1
                st.request_count = 0
                cookie = f"TOKEN=tok{st.cookie_counter}"
                st.cookies = {cookie}
                return 200, {"Set-Cookie": cookie + "; Path=/",
                             "X-CSRF-Token": st.csrf}, {"ok": True}
            return 401, {}, {"error": "bad credentials"}

        # --- ab hier: Cookie-Pflicht + Session-Ablauf ---
        cookie = (headers.get("cookie") or "").split(";")[0].strip()
        if cookie not in st.cookies:
            return 401, {}, {"error": "not logged in"}
        if (st.session_max_requests is not None
                and st.request_count >= st.session_max_requests):
            st.cookies.discard(cookie)
            return 401, {}, {"error": "session expired"}
        st.request_count += 1

        m = _RE_API.match(path)
        if not m:
            return 404, {}, {"error": "not found"}
        sub = m.group(2)

        if method == "GET" and sub == "/stat/device":
            return 200, {}, {"data": st.devices}

        if method in ("PUT", "POST"):
            if headers.get("x-csrf-token") != st.csrf:
                return 403, {}, {"error": "csrf token missing/wrong"}
            try:
                payload = json.loads(body.decode() or "{}")
            except json.JSONDecodeError:
                return 400, {}, {"error": "invalid json"}

            dm = re.match(r"^/rest/device/(.+)$", sub)
            if method == "PUT" and dm:
                dev_id = dm.group(1)
                dev = next((d for d in st.devices if d["_id"] == dev_id), None)
                if not dev:
                    return 404, {}, {"error": "unknown device"}
                dev["port_overrides"] = payload.get("port_overrides", [])
                st.puts.append((dev_id, payload))
                return 200, {}, {"ok": True}

            if method == "POST" and sub == "/cmd/devmgr":
                if payload.get("cmd") == "force-provision":
                    st.provisions.append(payload.get("mac", ""))
                    return 200, {}, {"ok": True}
                return 400, {}, {"error": "unknown cmd"}

        return 404, {}, {"error": "not found"}

    # ---------- HTTP-Server ----------

    def start(self) -> int:
        mock = self

        class Handler(BaseHTTPRequestHandler):
            def _run(self, method):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                status, hdrs, resp = mock.handle(method, self.path,
                                                 dict(self.headers), body)
                data = json.dumps(resp).encode()
                self.send_response(status)
                for k, v in hdrs.items():
                    self.send_header(k, v)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self._run("GET")

            def do_POST(self):
                self._run("POST")

            def do_PUT(self):
                self._run("PUT")

            def log_message(self, *a):
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        daemon=True)
        self._thread.start()
        return self._server.server_address[1]

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            if self._thread:
                self._thread.join(timeout=2)
            self._server = None
            self._thread = None


if __name__ == "__main__":
    m = ControllerMock()
    port = m.start()
    print(f"Controller-Mock lauscht auf http://127.0.0.1:{port} "
          f"(User: bridge / pw) - Strg+C beendet")
    try:
        m._thread.join()
    except KeyboardInterrupt:
        m.stop()
