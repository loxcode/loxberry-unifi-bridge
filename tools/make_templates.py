#!/usr/bin/env python3
"""CLI zum Erzeugen der Loxone-Vorlagen fuer die loxcode bridge.

Die eigentliche Generierung liegt in bridge/loxone_templates.py (einzige
Quelle, auch von der Bridge genutzt). Dieses Skript ist der Datei-Wrapper.

Aufruf (Beispiel):
  python3 tools/make_templates.py --bridge-host 192.168.1.50 \
      --api-user loxone --api-pass geheim \
      --switch "Rack=aa:bb:cc:dd:ee:ff=1,2,8" --switch "Flex=11:22:33:44:55:66=4"
Ohne Argumente entsteht eine Platzhalter-Version in templates/.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "bridge"))
from loxone_templates import (  # noqa: E402, F401
    base_address, build_vo_commands, build_vi_devices,
    render_vo_xml, render_vi_xml, render_files)

DEFAULT_SWITCH = "Switch1=aa:bb:cc:dd:ee:ff=1,2,3,4"


def parse_switch_arg(s: str) -> dict:
    name, mac, ports = s.split("=")
    return {"name": name, "mac": mac,
            "ports": [int(p) for p in ports.split(",") if p.strip()]}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bridge-host", default="192.168.1.50")
    p.add_argument("--bridge-port", type=int, default=5000)
    p.add_argument("--api-user", default="")
    p.add_argument("--api-pass", default="")
    p.add_argument("--switch", action="append", default=[],
                   help='Format: "Name=mac=1,2,3" (mehrfach erlaubt)')
    p.add_argument("--out-dir", default=None)
    a = p.parse_args()
    cfg = {"bridge_host": a.bridge_host, "bridge_port": a.bridge_port,
           "api_user": a.api_user, "api_pass": a.api_pass}
    switches = [parse_switch_arg(s) for s in (a.switch or [DEFAULT_SWITCH])]
    out_dir = pathlib.Path(a.out_dir) if a.out_dir else (
        pathlib.Path(__file__).resolve().parents[1] / "templates")
    out_dir.mkdir(exist_ok=True)
    for name, content in render_files(cfg, switches).items():
        (out_dir / name).write_text(content, encoding="utf-8")
    print(f"Vorlagen geschrieben nach {out_dir}")


if __name__ == "__main__":
    main()
