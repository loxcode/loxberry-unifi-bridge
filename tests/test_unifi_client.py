import sys, pathlib, unittest

BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "tools"))
sys.path.insert(0, str(BASE_DIR / "bridge"))
from controller_mock import ControllerMock
from unifi_client import UnifiClient

MAC = "aa:bb:cc:dd:ee:ff"


class ClientTestBase(unittest.TestCase):
    def setUp(self):
        self.mock = ControllerMock()
        port = self.mock.start()
        self.client = UnifiClient(f"http://127.0.0.1:{port}",
                                  username="bridge", password="pw")

    def tearDown(self):
        self.mock.stop()


class TestSetPoe(ClientTestBase):
    def test_set_poe_off_writes_override_and_provisions(self):
        ok, msg = self.client.set_poe(MAC, [1, 3], "off")
        self.assertTrue(ok, msg)
        overrides = self.mock.state.devices[0]["port_overrides"]
        self.assertEqual(
            sorted((o["port_idx"], o["poe_mode"], o["setting_preference"])
                   for o in overrides),
            [(1, "off", "manual"), (3, "off", "manual")])
        self.assertEqual(self.mock.state.provisions, [MAC])

    def test_set_poe_unknown_mac_fails(self):
        ok, msg = self.client.set_poe("00:00:00:00:00:00", [1], "on")
        self.assertFalse(ok)

    def test_auto_relogin_after_session_expiry(self):
        self.mock.state.session_max_requests = 2
        ok, _ = self.client.set_poe(MAC, [1], "off")   # >2 Requests noetig
        self.assertTrue(ok)
        self.assertGreaterEqual(self.mock.state.login_count, 2)


class TestStatus(ClientTestBase):
    def test_poe_status_from_table_and_overrides(self):
        self.assertEqual(self.client.poe_status(MAC, [1, 2]),
                         {1: "on", 2: "off"})
        self.client.set_poe(MAC, [1], "off")
        self.assertEqual(self.client.poe_status(MAC, [1])[1], "off")

    def test_poe_power(self):
        self.assertEqual(self.client.poe_power(MAC, [1, 2, 99]),
                         {1: 4.5, 2: 0.0, 99: 0.0})

    def test_device_online(self):
        self.assertTrue(self.client.device_online(MAC))
        self.mock.state.devices[0]["state"] = 0
        self.assertFalse(self.client.device_online(MAC))
        self.assertIsNone(self.client.device_online("00:00:00:00:00:00"))


class TestDiscover(ClientTestBase):
    def test_discover_switches_lists_poe_ports(self):
        found = self.client.discover_switches()
        self.assertEqual(len(found), 1)
        sw = found[0]
        self.assertEqual(sw["mac"], MAC)
        self.assertEqual(sw["name"], "Switch24")
        self.assertEqual(sw["model"], "USW-24-PoE")
        # port_table hat 3 PoE-Ports (poe_mode gesetzt)
        self.assertEqual(sw["poe_ports"], [1, 2, 3])
        self.assertEqual(sw["poe_power"], {1: 4.5, 2: 0.0, 3: 2.1})
        self.assertTrue(sw["online"])

    def test_discover_skips_devices_without_poe(self):
        self.mock.state.devices[0]["port_table"] = [
            {"port_idx": 1}, {"port_idx": 2}]  # keine poe_mode-Felder
        self.assertEqual(self.client.discover_switches(), [])


if __name__ == "__main__":
    unittest.main()
