import os, pathlib, shutil, subprocess, sys, tempfile, unittest, zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from build_loxberry_zip import build_zip, plugin_version

ROOT = pathlib.Path(__file__).resolve().parents[1]


class TestZip(unittest.TestCase):
    def test_zip_contains_plugin_structure_and_app(self):
        path = build_zip()
        self.assertRegex(path.name, r"^loxcode_bridge-\d+\.\d+\.\d+\.zip$")
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
        for required in ("plugin.cfg", "dpkg/apt", "daemon/daemon.sh",
                         "LICENSE",
                         "bin/app.py", "bin/unifi_client.py",
                         "bin/restart.sh", "bin/config.default.json",
                         "bin/loxone_templates.py", "cron/cron.05min",
                         "postinstall.sh", "preupgrade.sh", "postupgrade.sh",
                         "icons/icon.svg",
                         # LoxBerry erwartet PNG-Icons in festen Groessen
                         "icons/icon_64.png", "icons/icon_128.png",
                         "icons/icon_256.png", "icons/icon_512.png",
                         # LoxBerry kopiert htmlauth/-Inhalt selbst nach
                         # plugins/<ordner>/ - KEIN plugins/-Prefix im ZIP!
                         "webfrontend/htmlauth/index.php",
                         "webfrontend/htmlauth/help.php"):
            self.assertIn(required, names, f"{required} fehlt im ZIP")

    def test_zip_has_no_nested_plugins_folder(self):
        path = build_zip()
        with zipfile.ZipFile(path) as z:
            nested = [n for n in z.namelist()
                      if n.startswith("webfrontend/htmlauth/plugins/")]
        self.assertEqual(nested, [], "verschachtelte plugins/-Struktur im ZIP")

    def test_zip_ships_no_config_json_in_config_folder(self):
        # config.json darf NICHT im auto-kopierten config/-Ordner liegen -
        # sonst ueberschreibt jedes Update die Nutzer-Konfiguration.
        path = build_zip()
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
        self.assertNotIn("config/config.json", names)
        self.assertFalse([n for n in names if n.startswith("config/")],
                         "config/-Ordner wird beim Update ueberschrieben")

    def test_webfrontend_links_and_ships_help_page(self):
        index = (ROOT / "loxberry" / "webfrontend" / "htmlauth" / "index.php").read_text(
            encoding="utf-8")
        help_page = (ROOT / "loxberry" / "webfrontend" / "htmlauth" / "help.php").read_text(
            encoding="utf-8")
        self.assertIn('href="help.php"', index)
        self.assertIn("Hilfe &amp; Anleitung", index)
        self.assertIn("Wofür ist das Plugin gedacht?", help_page)
        self.assertIn("Loxone verwenden", help_page)
        self.assertIn("Fehlersuche", help_page)

    def _run_hook(self, name, lbhome, temp_path, folder="loxcode_bridge"):
        env = os.environ.copy()
        env.update({
            "LBHOMEDIR": str(lbhome),
            "LBPCONFIG": str(lbhome / "config" / "plugins"),
            "LBPBIN": str(lbhome / "bin" / "plugins"),
        })
        return subprocess.run(
             ["bash", str(ROOT / "loxberry" / name),
             "installtmp", "loxcode_bridge", folder, plugin_version(),
             str(lbhome), str(temp_path)],
            cwd=str(ROOT), env=env, check=True,
            capture_output=True, text=True)

    def test_upgrade_hooks_restore_existing_config_after_update_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            lbhome = pathlib.Path(tmp) / "lbhome"
            folder = "loxcode_bridge_abc"
            cfgdir = lbhome / "config" / "plugins" / folder
            bindir = lbhome / "bin" / "plugins" / folder
            cfgdir.mkdir(parents=True)
            bindir.mkdir(parents=True)
            shutil.copy2(ROOT / "loxberry" / "bin" / "config.default.json",
                         bindir / "config.default.json")
            shutil.copy2(ROOT / "loxberry" / "bin" / "restart.sh",
                         bindir / "restart.sh")

            custom_config = (
                '{\n'
                '  "UNIFI_HOST": "https://10.0.0.1",\n'
                '  "UNIFI_SITE": "default",\n'
                '  "UNIFI_USER": "user",\n'
                '  "UNIFI_PASS": "secret",\n'
                '  "DEFAULT_TIMEOUT": "9.5",\n'
                '  "API_USER": "loxone",\n'
                '  "API_PASS": "api-secret",\n'
                '  "SWITCHES_JSON": "{\\"Rack\\":\\"aa:bb:cc:dd:ee:ff\\"}",\n'
                '  "BRIDGE_PORT": "5050"\n'
                '}')
            (cfgdir / "config.json").write_text(custom_config, encoding="utf-8")
            (cfgdir / "local-note.txt").write_text("keep me", encoding="utf-8")

            temp_path = pathlib.Path(tmp) / "upgrade-temp"
            self._run_hook("preupgrade.sh", lbhome, temp_path, folder)

            shutil.rmtree(cfgdir)
            cfgdir.mkdir(parents=True)
            self._run_hook("postinstall.sh", lbhome, temp_path, folder)
            self.assertNotEqual(
                custom_config,
                (cfgdir / "config.json").read_text(encoding="utf-8"))

            self._run_hook("postupgrade.sh", lbhome, temp_path, folder)

            self.assertEqual(
                custom_config,
                (cfgdir / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(
                "keep me",
                (cfgdir / "local-note.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
