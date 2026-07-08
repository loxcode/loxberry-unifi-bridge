import sys, pathlib, unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import make_templates as mt

CFG = {"bridge_host": "192.168.1.50", "bridge_port": 5000,
       "api_user": "loxone", "api_pass": "geheim"}
SW = [mt.parse_switch_arg("Rack=aa:bb:cc:dd:ee:ff=1,2"),
      mt.parse_switch_arg("Flex=11:22:33:44:55:66=4")]


class TestParsing(unittest.TestCase):
    def test_parse_switch_arg(self):
        s = mt.parse_switch_arg("Rack=aa:bb:cc:dd:ee:ff=1,2,8")
        self.assertEqual(s, {"name": "Rack", "mac": "aa:bb:cc:dd:ee:ff",
                             "ports": [1, 2, 8]})

    def test_base_address_with_and_without_auth(self):
        self.assertEqual(mt.base_address(CFG),
                         "http://loxone:geheim@192.168.1.50:5000")
        cfg = dict(CFG, api_user="", api_pass="")
        self.assertEqual(mt.base_address(cfg), "http://192.168.1.50:5000")


class TestVo(unittest.TestCase):
    def test_commands(self):
        cmds = mt.build_vo_commands(SW)
        # 2+1 Ports einzeln + 2 "alle Ports" = 5
        self.assertEqual(len(cmds), 5)
        first = cmds[0]
        self.assertEqual(first["title"], "Rack Port 1 PoE")
        self.assertEqual(first["cmd_on"],
                         "/poe/set?switch=Rack&ports=1&state=on")
        self.assertEqual(first["cmd_off"],
                         "/poe/set?switch=Rack&ports=1&state=off")
        alle = next(c for c in cmds if c["title"] == "Rack alle Ports PoE")
        self.assertEqual(alle["cmd_on"],
                         "/poe/set?switch=Rack&ports=1,2&state=on")

    def test_vo_xml(self):
        root = ET.fromstring(mt.render_vo_xml(CFG, SW))
        self.assertEqual(root.tag, "VirtualOut")
        self.assertEqual(root.get("Address"),
                         "http://loxone:geheim@192.168.1.50:5000")
        self.assertEqual(len(root.findall("VirtualOutCmd")), 5)


class TestVi(unittest.TestCase):
    def test_vi_devices(self):
        devs = mt.build_vi_devices(CFG, SW)
        self.assertEqual(len(devs), 6)  # 3 je Switch
        status = next(d for d in devs
                      if d["filename"] == "VI_Rack_status.xml")
        self.assertIn("/poe/status.txt?switch=Rack&ports=1,2", status["url"])
        self.assertEqual([c["check"] for c in status["cmds"]],
                         ["port1=\\v", "port2=\\v"])
        online = next(d for d in devs
                      if d["filename"] == "VI_Rack_online.xml")
        self.assertEqual(online["cmds"][0]["check"], "online=\\v")

    def test_vi_xml(self):
        dev = mt.build_vi_devices(CFG, SW)[0]
        root = ET.fromstring(mt.render_vi_xml(dev))
        self.assertEqual(root.tag, "VirtualInHttp")
        self.assertEqual(root.get("PollingTime"), "30")
        self.assertTrue(root.get("Address").startswith(
            "http://loxone:geheim@192.168.1.50:5000/poe/status.txt"))
        self.assertEqual(len(root.findall("VirtualInHttpCmd")), 2)


if __name__ == "__main__":
    unittest.main()
