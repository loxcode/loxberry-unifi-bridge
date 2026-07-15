#!/usr/bin/env python3
# loxcode bridge - Copyright (C) 2026 loxcode
# Lizenz: GNU General Public License v3.0 - siehe LICENSE im Projekt-Root.
"""Erzeugt die Loxone-Vorlagen (virtueller Ausgang + HTTP-Eingänge) für
die loxcode bridge. Einzige Quelle - genutzt von der Bridge (/templates.zip)
und vom CLI-Wrapper tools/make_templates.py.

Ein `switch` ist ein dict {"name": str, "mac": str, "ports": list[int]}.
`cfg` ist ein dict {bridge_host, bridge_port, api_user, api_pass}.
"""
import io
import re
import zipfile
from urllib.parse import quote
from xml.sax.saxutils import quoteattr

_XML_HEAD = '<?xml version="1.0" encoding="utf-8"?>\n'
_GEN_NOTE = ("<!-- UniFi Bridge v1.0.19 - generiert von "
             "tools/make_templates.py -->\n")


def base_address(cfg: dict) -> str:
    auth = ""
    if cfg.get("api_user") and cfg.get("api_pass"):
        user = quote(str(cfg["api_user"]), safe="")
        password = quote(str(cfg["api_pass"]), safe="")
        auth = f"{user}:{password}@"
    return f"http://{auth}{cfg['bridge_host']}:{cfg['bridge_port']}"


def safe_filename_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "")).strip("._")
    return cleaned[:64] or "Switch"


def switch_query_name(value: str) -> str:
    return quote(str(value or ""), safe="")


def build_vo_commands(switches: list) -> list:
    cmds = []
    for sw in switches:
        query_name = switch_query_name(sw["name"])
        for p in sw["ports"]:
            cmds.append({
                "title": f"{sw['name']} Port {p} PoE",
                "cmd_on": f"/poe/set?switch={query_name}&ports={p}&state=on",
                "cmd_off": f"/poe/set?switch={query_name}&ports={p}&state=off",
            })
        allp = ",".join(str(p) for p in sw["ports"])
        cmds.append({
            "title": f"{sw['name']} alle Ports PoE",
            "cmd_on": f"/poe/set?switch={query_name}&ports={allp}&state=on",
            "cmd_off": f"/poe/set?switch={query_name}&ports={allp}&state=off",
        })
    return cmds


def render_vo_xml(cfg: dict, switches: list) -> str:
    lines = [_XML_HEAD, _GEN_NOTE,
             f'<VirtualOut Title="loxcode bridge PoE" '
             f'Comment="PoE dauerhaft an/aus via loxcode bridge - siehe README" '
             f'Address={quoteattr(base_address(cfg))} '
             'CmdInit="" CloseAfterSend="true" CmdSep="">\n']
    for c in build_vo_commands(switches):
        lines.append(
            "\t<VirtualOutCmd"
            f" Title={quoteattr(c['title'])}"
            ' Comment="" CmdOnMethod="GET"'
            f" CmdOn={quoteattr(c['cmd_on'])}"
            ' CmdOnHTTP="" CmdOnPost="" CmdOffMethod="GET"'
            f" CmdOff={quoteattr(c['cmd_off'])}"
            ' CmdOffHTTP="" CmdOffPost=""'
            ' Analog="false" Repeat="0" RepeatRate="0"/>\n')
    lines.append("</VirtualOut>\n")
    return "".join(lines)


def build_vi_devices(cfg: dict, switches: list) -> list:
    base = base_address(cfg)
    devs = []
    for sw in switches:
        ports = ",".join(str(p) for p in sw["ports"])
        query_name = switch_query_name(sw["name"])
        filename_name = safe_filename_part(sw["name"])
        devs.append({
            "filename": f"VI_{filename_name}_status.xml",
            "title": f"loxcode bridge {sw['name']} PoE-Status",
            "url": f"{base}/poe/status.txt?switch={query_name}&ports={ports}",
            "polling": 30,
            "cmds": [{"title": f"{sw['name']} Port {p} PoE",
                      "check": f"port{p}=\\v"} for p in sw["ports"]],
        })
        devs.append({
            "filename": f"VI_{filename_name}_power.xml",
            "title": f"loxcode bridge {sw['name']} PoE-Leistung",
            "url": f"{base}/poe/power.txt?switch={query_name}&ports={ports}",
            "polling": 60,
            "cmds": [{"title": f"{sw['name']} Port {p} Watt",
                      "check": f"port{p}=\\v"} for p in sw["ports"]],
        })
        devs.append({
            "filename": f"VI_{filename_name}_online.xml",
            "title": f"loxcode bridge {sw['name']} Online",
            "url": f"{base}/device/status.txt?switch={query_name}",
            "polling": 60,
            "cmds": [{"title": f"{sw['name']} Online", "check": "online=\\v"}],
        })
    return devs


def render_vi_xml(dev: dict) -> str:
    lines = [_XML_HEAD, _GEN_NOTE,
             f'<VirtualInHttp Title={quoteattr(dev["title"])} '
             'Comment="" '
             f'Address={quoteattr(dev["url"])} '
             f'PollingTime={quoteattr(str(dev["polling"]))}>\n']
    for c in dev["cmds"]:
        lines.append(
            "\t<VirtualInHttpCmd"
            f" Title={quoteattr(c['title'])}"
            ' Comment=""'
            f" Check={quoteattr(c['check'])}"
            ' Analog="true" Signed="true"'
            ' SourceValLow="0" DestValLow="0" SourceValHigh="0"'
            ' DestValHigh="0" DefVal="0" MinVal="-2147483647"'
            ' MaxVal="2147483647"/>\n')
    lines.append("</VirtualInHttp>\n")
    return "".join(lines)


def render_files(cfg: dict, switches: list) -> dict:
    """Alle Vorlagen als {Dateiname: XML-Text}."""
    files = {"VO_loxcodeBridge.xml": render_vo_xml(cfg, switches)}
    for dev in build_vi_devices(cfg, switches):
        files[dev["filename"]] = render_vi_xml(dev)
    return files


def build_zip_bytes(cfg: dict, switches: list) -> bytes:
    """Alle Vorlagen als ZIP im Speicher (für den Webfrontend-Download)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in render_files(cfg, switches).items():
            z.writestr(name, content)
    return buf.getvalue()
