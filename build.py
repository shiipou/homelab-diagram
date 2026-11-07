#!/usr/bin/env python3
"""Render the network in inventory.yaml as an SVG and PNG."""
import base64
import html
import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent
INV = yaml.safe_load((ROOT / "inventory.yaml").read_text())
ICONS = ROOT / "icons"
OUT = ROOT / "out"
UNREDACTED = "--unredacted" in sys.argv

W, H = 2400, 1460
BG = "#0b0f15"
GRID = "#151c26"
PANEL = "#111821"
PANEL2 = "#161f2b"
CHIP = "#19222e"
BORDER = "#253042"
TEXT = "#e6edf3"
MUTED = "#8d9aab"
FAINT = "#5d6a7c"
LINK = "#79c0ff"
CP = "#58a6ff"
WORKER = "#bc8cff"
STORAGE = "#c08a5c"
WAN = "#f0883e"
TRUNK = "#d5dde6"


class SVG:
    def __init__(self):
        self.parts = []
        self.icon_cache = {}

    def add(self, value):
        self.parts.append(value)

    def rect(self, x, y, w, h, fill=PANEL, stroke=BORDER, sw=1.4, rx=12, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>'
        )

    def text(self, x, y, value, size=14, fill=TEXT, weight=400, anchor="start", mono=False):
        family = "Fira Code" if mono else "Fira Sans"
        self.add(
            f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">'
            f'{html.escape(str(value), quote=True)}</text>'
        )

    def line(self, points, color, width=3, dash=None):
        d = " ".join(f"{x},{y}" for x, y in points)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(
            f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round"{dash_attr}/>'
        )

    def icon(self, name, x, y, size):
        if name not in self.icon_cache:
            path = ICONS / f"{name}.svg"
            if not path.exists():
                raise SystemExit(f"missing icon '{name}'")
            self.icon_cache[name] = base64.b64encode(path.read_bytes()).decode()
        self.add(
            f'<image x="{x}" y="{y}" width="{size}" height="{size}" '
            f'href="data:image/svg+xml;base64,{self.icon_cache[name]}"/>'
        )

    def render(self):
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}">'
            + "".join(self.parts)
            + "</svg>"
        )


S = SVG()


def panel(x, y, w, h, title, subtitle=None, stroke=BORDER):
    S.rect(x, y, w, h, stroke=stroke)
    S.text(x + 20, y + 32, title, 19, TEXT, 600)
    if subtitle:
        S.text(x + 20, y + 54, subtitle, 12.5, MUTED)


def endpoint(x, y, w, h, title, lines, icon, accent):
    S.rect(x, y, w, h, fill=PANEL2, stroke=accent + "99")
    S.icon(icon, x + 18, y + (h - 48) / 2, 48)
    S.text(x + 82, y + 34, title, 19, TEXT, 600)
    for i, line in enumerate(lines):
        S.text(x + 82, y + 60 + i * 19, line, 13, MUTED if i else accent, 500)


def port_box(x, y, w, h, label, target, color, badge=None):
    S.rect(x, y, w, h, fill=CHIP, stroke=color + "88", rx=9)
    S.text(x + 12, y + 22, label, 12, color, 600, mono=True)
    if badge:
        S.rect(x + w - 58, y + 8, 46, 18, fill=color + "22", stroke=color + "88", sw=1, rx=9)
        S.text(x + w - 35, y + 21, badge, 9.5, color, 600, anchor="middle")
    S.text(x + 12, y + 43, target, 12.5, TEXT, 500)


def role_tag(x, y, label, color):
    width = max(90, len(label) * 7.3 + 22)
    S.rect(x - width, y, width, 23, fill=color + "22", stroke=color + "88", sw=1, rx=12)
    S.text(x - width / 2, y + 16, label, 11, color, 600, anchor="middle")


def node_card(node, x, y, w, h):
    is_storage = node.get("storage", False)
    role_color = STORAGE if is_storage else CP if node["role"] == "Control plane" else WORKER
    icon = "glyph-ssd" if is_storage else "glyph-gpu" if "GPU" in node["name"] else "glyph-cpu"
    S.rect(x, y, w, h, fill=PANEL, stroke=role_color + "aa", sw=1.6)
    S.rect(x + 1, y + 14, 4, h - 28, fill=role_color, stroke="none", sw=0, rx=2)
    S.icon(icon, x + 18, y + 18, 42)
    S.text(x + 72, y + 35, node["name"], 19, TEXT, 600)
    role_tag(x + w - 16, y + 13, "STORAGE" if is_storage else node["role"].upper(), role_color)
    S.text(x + 22, y + 83, node["model"], 14, TEXT, 500)
    if is_storage:
        S.text(x + 22, y + 106, "8 GB RAM · separate storage appliance", 12.5, MUTED)
        details = INV["storage"]["devices"]
        for i, item in enumerate(details):
            S.text(x + 22, y + 139 + i * 20, item, 12.5, TEXT, 400)
    else:
        S.text(x + 22, y + 106, INV["kubernetes"]["name"], 12.5, MUTED)
        S.text(x + 22, y + 132, node["ip"], 14, role_color, 600, mono=True)
        for i, spec in enumerate(node.get("specs", [])):
            S.text(x + 22, y + 164 + i * 19, spec, 12.5, TEXT, 400)
    S.line([(x + 18, y + h - 35), (x + w - 18, y + h - 35)], BORDER, 1)
    S.text(x + 22, y + h - 15, node["connection"], 11.5, MUTED, 500)


def by_port(items, pattern):
    def port_number(item):
        import re
        match = re.search(pattern, item["connection"])
        return int(match.group(1)) if match else 0
    return sorted(items, key=port_number)


# Background and title
S.add(
    f'<defs><pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">'
    f'<circle cx="1.5" cy="1.5" r="1.2" fill="{GRID}"/></pattern></defs>'
)
S.rect(0, 0, W, H, fill=BG, stroke=BG, sw=0, rx=0)
S.add(f'<rect width="{W}" height="{H}" fill="url(#dots)"/>')
meta = INV["meta"]
S.text(42, 78, meta["title"], 44, TEXT, 700)
S.text(44, 108, "Freebox + 5G failover · OpenWrt · Talos Kubernetes", 16, MUTED)
S.text(W - 42, 78, meta["date"], 15, MUTED, 400, "end")

# Internet edge
endpoint(42, 165, 286, 140, "Internet", ["Freebox primary", "5G cellular failover"], "glyph-nic", LINK)
endpoint(
    400, 165, 470, 140, INV["freebox"]["name"],
    [INV["freebox"]["model"], f"Gateway · {INV['freebox']['ip']}"],
    "glyph-nic", WAN
)
endpoint(
    970, 165, 720, 140, INV["mochabin"]["name"],
    [f"WAN · {INV['mochabin']['wan']}", f"LAN · {INV['mochabin']['lan']} · {INV['mochabin']['os']}"],
    "glyph-nic", CP
)
endpoint(1888, 165, 470, 140, "5G backup", ["5G card · unlimited data SIM", "Failover WAN"], "glyph-antenna", LINK)
S.line([(328, 235), (400, 235)], LINK, 3)
S.line([(870, 235), (970, 235)], WAN, 5)
S.text(920, 223, INV["freebox"]["link"], 11, WAN, 600, anchor="middle", mono=True)
S.line([(1690, 235), (1888, 235)], LINK, 2.5, dash="5 6")
S.text(1789, 223, "FAILOVER", 11, LINK, 600, anchor="middle", mono=True)

# MochaBin port map
px, py, pw, ph = 42, 355, 1470, 290
mochabin_ports = INV["mochabin"]["ports"]
panel(px, py, pw, ph, "MochaBin port map", "eth0 faces left · eth1 empty · eth2 uplink · lan0–lan3 direct LAN")
port_box(62, 430, 210, 78, "eth0", mochabin_ports["eth0"], WAN, "SFP+")
port_box(284, 430, 210, 78, "eth1", mochabin_ports["eth1"], FAINT, "SFP+")
port_box(506, 430, 240, 78, "eth2", mochabin_ports["eth2"], CP)
S.text(785, 422, "2 × 2 LAN PORT GROUP", 11, STORAGE, 700)
lan_ports = [
    ("lan0", mochabin_ports["lan0"]),
    ("lan1", mochabin_ports["lan1"]),
    ("lan2", mochabin_ports["lan2"]),
    ("lan3", mochabin_ports["lan3"]),
]
for i, (label, target) in enumerate(lan_ports):
    col, row = i % 2, i // 2
    port_box(785 + col * 345, 435 + row * 84, 330, 68, label, target, STORAGE)
S.text(px + 22, py + ph - 21, "LAN gateway 172.26.0.1/16", 13, CP, 600, mono=True)

# Cilium / VIPs / ingress
bx, by, bw, bh = 1540, 355, 818, 290
panel(bx, by, bw, bh, "Cilium BGP", f"Talos cluster · {INV['network']['subnet']}", stroke=CP + "88")
for i, vip in enumerate(INV["bgp"]["vip_services"]):
    yy = by + 74 + i * 45
    S.rect(bx + 18, yy, bw - 36, 36, fill=CHIP, stroke=BORDER, rx=8)
    S.text(bx + 32, yy + 23, vip["name"], 13, TEXT, 500)
    S.text(bx + bw - 32, yy + 23, vip["ip"], 13, CP, 600, anchor="end", mono=True)
S.text(bx + 24, by + bh - 22, "Internet ingress · TCP 80 / 443 → Traefik VIP", 13, LINK, 600)

# Kubernetes nodes
nodes = INV["nodes"]
direct = by_port([n for n in nodes if n["group"] == "MochaBin direct"], r"lan(\d+)")
lan_storage = dict(INV["storage"], name=INV["storage"]["name"], role="Storage", model=INV["storage"]["model"],
                   connection=INV["storage"]["connection"], storage=True)
direct.append(lan_storage)
sw_nodes = by_port([n for n in nodes if n["group"] == "GS308"], r"port (\d+)")
node_xs = [42, 632, 1222, 1812]
node_w, node_h = 546, 245
S.text(42, 713, "MOCHABIN 2 × 2 DIRECT LINKS", 13, STORAGE, 700)
S.text(2358, 713, "3 TALOS NODES + STORAGE", 12, MUTED, 500, "end")
for i, node in enumerate(direct):
    node_card(node, node_xs[i], 735, node_w, node_h)

S.text(42, 1040, "NETGEAR GS308 · UPLINK FROM MOCHABIN ETH2", 13, CP, 700)
S.text(2358, 1040, "GIGABIT SWITCH", 12, MUTED, 500, "end")
for i, node in enumerate(sw_nodes):
    node_card(node, node_xs[i], 1062, node_w, node_h)

# Switch port map
sx, sy, sw, sh = 42, 1352, 1470, 76
S.rect(sx, sy, sw, sh, fill=PANEL2, stroke=BORDER, rx=10)
S.text(sx + 18, sy + 29, INV["switch"]["name"], 14, TEXT, 600)
for i, port in enumerate(INV["switch"]["ports"]):
    cx = sx + 265 + i * 147
    color = CP if port["to"] != "Free" else FAINT
    target = port["to"].split(" · ")[0]
    target = target.replace("HP EliteDesk 800 G6 Mini", "HP Mini 2").replace("IBM dual-Xeon", "IBM")
    S.rect(cx, sy + 13, 135, 49, fill=CHIP, stroke=color + "88", rx=7)
    S.text(cx + 10, sy + 31, f"P{port['port']} · {target}", 10.5, color, 600)
    S.text(cx + 10, sy + 49, "in use" if port["to"] != "Free" else "free", 10, MUTED, 400)

S.text(42, 1450, "Control planes", 11, CP, 600)
S.text(175, 1450, "Workers", 11, WORKER, 600)
S.text(265, 1450, "Storage appliance", 11, STORAGE, 600)

OUT.mkdir(exist_ok=True)
name = "homelab-unredacted" if UNREDACTED else "homelab"
svg_path = OUT / f"{name}.svg"
png_path = OUT / f"{name}.png"
svg_path.write_text(S.render())
subprocess.run(["rsvg-convert", "-z", "1.6", "-o", str(png_path), str(svg_path)], check=True)
print(svg_path, png_path)
