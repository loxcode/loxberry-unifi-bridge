#!/usr/bin/env python3
"""Baut das installierbare LoxBerry-Plugin-ZIP der loxcode bridge.

Kopiert den Bridge-Kern (app.py, unifi_client.py) in die bin/-Struktur
und zippt das Plugin gemaess LoxBerry-Interface-2.0-Layout.
"""
import configparser
import pathlib
import shutil
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def plugin_version() -> str:
    cp = configparser.ConfigParser()
    cp.read(ROOT / "loxberry" / "plugin.cfg")
    return cp["PLUGIN"]["VERSION"]


def build_zip(version=None) -> pathlib.Path:
    version = version or plugin_version()
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    out = dist / f"loxcode_bridge-{version}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        stage = pathlib.Path(tmp) / "plugin"
        shutil.copytree(ROOT / "loxberry", stage)
        for src in ("app.py", "unifi_client.py", "loxone_templates.py"):
            shutil.copy2(ROOT / "bridge" / src, stage / "bin" / src)
        # GPL verlangt, dass die Lizenz mit dem Programm ausgeliefert wird
        # (produkt-eigene Kopie, damit die Bridge self-contained bleibt)
        license_file = ROOT / "LICENSE"
        if license_file.exists():
            shutil.copy2(license_file, stage / "LICENSE")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(stage.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(stage))
    return out


if __name__ == "__main__":
    print(build_zip())
