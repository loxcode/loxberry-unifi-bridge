import base64
import io
import pathlib
import sys
import unittest
import zipfile

BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "tools"))
sys.path.insert(0, str(BASE_DIR / "bridge"))
from controller_mock import ControllerMock  # noqa: E402
from unifi_client import UnifiClient  # noqa: E402
from app import create_app  # noqa: E402

MAC = "aa:bb:cc:dd:ee:ff"
AUTH = {"Authorization":
        "Basic " + base64.b64encode(b"loxone:geheim").decode()}


class AppTestBase(unittest.TestCase):
    def setUp(self):
        self.mock = ControllerMock()
        port = self.mock.start()
        client = UnifiClient(f"http://127.0.0.1:{port}",
                             username="bridge", password="pw",
                             device_cache_ttl=0)
        self.client = client
        app = create_app(client, {"Switch24": MAC},
                         api_user="loxone", api_pass="geheim")
        self.http = app.test_client()

    def tearDown(self):
        self.client.close()
        self.mock.stop()


class TestAuthAndHealth(AppTestBase):
    def test_health_without_auth(self):
        r = self.http.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["status"], "ok")

    def test_endpoints_require_basic_auth(self):
        r = self.http.get("/poe/status?switch=Switch24&ports=1")
        self.assertEqual(r.status_code, 401)

    def test_selftest_requires_auth_and_reports_chain(self):
        self.assertEqual(self.http.get("/selftest").status_code, 401)
        r = self.http.get("/selftest", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data["unifi_reachable"])
        self.assertTrue(data["login_ok"])
        self.assertEqual(data["switches_found"], ["Switch24"])
        self.assertEqual(data["switches_missing"], [])
        # darf keine Zugangsdaten/MACs enthalten
        self.assertNotIn("aa:bb:cc:dd:ee:ff", r.get_data(as_text=True))

    def test_selftest_flags_missing_switch(self):
        self.mock.state.devices[0]["mac"] = "99:99:99:99:99:99"
        data = self.http.get("/selftest", headers=AUTH).get_json()
        self.assertEqual(data["switches_missing"], ["Switch24"])

    def test_missing_api_credentials_lock_non_health_endpoints(self):
        app = create_app(self.client, {"Switch24": MAC})
        http = app.test_client()
        self.assertEqual(http.get("/health").status_code, 200)
        self.assertEqual(
            http.get("/poe/set?switch=Switch24&ports=1&state=off").status_code,
            503,
        )


class TestDiscoverEndpoint(AppTestBase):
    def test_devices_requires_auth(self):
        self.assertEqual(self.http.get("/devices").status_code, 401)

    def test_devices_lists_switches_with_poe(self):
        r = self.http.get("/devices", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["switches"]), 1)
        sw = data["switches"][0]
        self.assertEqual(sw["mac"], MAC)
        self.assertEqual(sw["poe_ports"], [1, 2, 3])


class TestTemplatesDownload(AppTestBase):
    def test_requires_auth(self):
        self.assertEqual(self.http.get("/templates.zip").status_code, 401)

    def test_returns_zip_with_templates_for_configured_switch(self):
        r = self.http.get("/templates.zip?host=192.168.178.20", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content_type, "application/zip")
        self.assertIn("attachment", r.headers.get("Content-Disposition", ""))
        with zipfile.ZipFile(io.BytesIO(r.get_data())) as z:
            names = z.namelist()
            self.assertIn("VO_loxcodeBridge.xml", names)
            self.assertIn("VI_Switch24_status.xml", names)
            vo = z.read("VO_loxcodeBridge.xml").decode()
        # Ports kommen aus der Discovery (1,2,3), Host aus dem Query-Param
        self.assertIn("192.168.178.20", vo)
        self.assertIn("switch=Switch24&amp;ports=3&amp;state=on", vo)

    def test_error_when_switch_not_found_in_controller(self):
        self.mock.state.devices[0]["mac"] = "77:77:77:77:77:77"
        r = self.http.get("/templates.zip?host=1.2.3.4", headers=AUTH)
        self.assertEqual(r.status_code, 409)
        self.assertFalse(r.get_json()["ok"])


class TestPoeSet(AppTestBase):
    def test_set_off_and_compat_response(self):
        r = self.http.get(
            "/poe/set?switch=Switch24&ports=1,3&state=off", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["ok"])
        modes = {o["port_idx"]: o["poe_mode"]
                 for o in self.mock.state.devices[0]["port_overrides"]}
        self.assertEqual(modes, {1: "off", 3: "off"})

    def test_unknown_switch_400(self):
        r = self.http.get(
            "/poe/set?switch=Nix&ports=1&state=on", headers=AUTH)
        self.assertEqual(r.status_code, 400)

    def test_bad_state_400(self):
        r = self.http.get(
            "/poe/set?switch=Switch24&ports=1&state=vielleicht", headers=AUTH)
        self.assertEqual(r.status_code, 400)

    def test_non_poe_port_is_rejected(self):
        r = self.http.get(
            "/poe/set?switch=Switch24&ports=99&state=off", headers=AUTH)
        self.assertEqual(r.status_code, 500)
        self.assertIn("Keine PoE-Ports", r.get_json()["message"])


class TestStatusFormats(AppTestBase):
    def test_status_json_compat(self):
        r = self.http.get(
            "/poe/status?switch=Switch24&ports=1,2", headers=AUTH)
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["ports"], {"1": "on", "2": "off"})

    def test_status_txt(self):
        r = self.http.get(
            "/poe/status.txt?switch=Switch24&ports=1,2", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content_type.startswith("text/plain"))
        self.assertEqual(r.get_data(as_text=True), "port1=1;port2=0")

    def test_status_txt_all_uniform(self):
        r = self.http.get(
            "/poe/status.txt?switch=Switch24&ports=1,3", headers=AUTH)
        self.assertEqual(r.get_data(as_text=True), "port1=1;port3=1;all=1")

    def test_power_txt(self):
        r = self.http.get(
            "/poe/power.txt?switch=Switch24&ports=1,2", headers=AUTH)
        self.assertEqual(r.get_data(as_text=True), "port1=4.5;port2=0.0")

    def test_device_status_txt(self):
        r = self.http.get(
            "/device/status.txt?switch=Switch24", headers=AUTH)
        self.assertEqual(r.get_data(as_text=True), "online=1")
        self.mock.state.devices[0]["state"] = 0
        r = self.http.get(
            "/device/status.txt?switch=Switch24", headers=AUTH)
        self.assertEqual(r.get_data(as_text=True), "online=0")


if __name__ == "__main__":
    unittest.main()
