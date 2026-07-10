import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from controller_mock import ControllerMock

LOGIN = ("POST", "/api/auth/login", {},
         json.dumps({"username": "bridge", "password": "pw"}).encode())


class TestControllerMock(unittest.TestCase):
    def setUp(self):
        self.mock = ControllerMock()

    def _login(self):
        status, headers, _ = self.mock.handle(*LOGIN)
        self.assertEqual(status, 200)
        cookie = headers["Set-Cookie"].split(";")[0]
        return {"Cookie": cookie, "X-CSRF-Token": headers["X-CSRF-Token"]}

    def test_login_wrong_password_401(self):
        body = json.dumps({"username": "bridge", "password": "falsch"}).encode()
        status, _, _ = self.mock.handle("POST", "/api/auth/login", {}, body)
        self.assertEqual(status, 401)

    def test_stat_device_requires_cookie(self):
        status, _, _ = self.mock.handle(
            "GET", "/proxy/network/api/s/default/stat/device", {}, b"")
        self.assertEqual(status, 401)
        h = self._login()
        status, _, body = self.mock.handle(
            "GET", "/proxy/network/api/s/default/stat/device", h, b"")
        self.assertEqual(status, 200)
        self.assertEqual(body["data"][0]["mac"], "aa:bb:cc:dd:ee:ff")

    def test_put_requires_csrf(self):
        h = self._login()
        payload = json.dumps({"port_overrides": [
            {"port_idx": 2, "poe_mode": "auto",
             "setting_preference": "manual"}]}).encode()
        no_csrf = {"Cookie": h["Cookie"]}
        status, _, _ = self.mock.handle(
            "PUT", "/proxy/network/api/s/default/rest/device/abc123",
            no_csrf, payload)
        self.assertEqual(status, 403)
        status, _, _ = self.mock.handle(
            "PUT", "/proxy/network/api/s/default/rest/device/abc123",
            h, payload)
        self.assertEqual(status, 200)
        self.assertEqual(self.mock.state.puts[-1][0], "abc123")
        self.assertEqual(
            self.mock.state.devices[0]["port_overrides"][0]["poe_mode"], "auto")

    def test_session_expiry_invalidates_cookie(self):
        self.mock.state.session_max_requests = 2
        h = self._login()
        path = "/proxy/network/api/s/default/stat/device"
        self.assertEqual(self.mock.handle("GET", path, h, b"")[0], 200)
        self.assertEqual(self.mock.handle("GET", path, h, b"")[0], 200)
        self.assertEqual(self.mock.handle("GET", path, h, b"")[0], 401)

    def test_devmgr_logs_provision(self):
        h = self._login()
        body = json.dumps({"cmd": "force-provision",
                           "mac": "aa:bb:cc:dd:ee:ff"}).encode()
        status, _, _ = self.mock.handle(
            "POST", "/api/s/default/cmd/devmgr", h, body)
        self.assertEqual(status, 200)
        self.assertEqual(self.mock.state.provisions,
                         ["aa:bb:cc:dd:ee:ff"])


if __name__ == "__main__":
    unittest.main()
