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

W, H = 2400, 1820
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
SPEED_W = {"1G": 2.4, "10G": 8.5}


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
S.line([(870, 235), (970, 235)], WAN, SPEED_W["10G"])
S.text(920, 223, INV["freebox"]["link"], 11, WAN, 600, anchor="middle", mono=True)
S.line([(1690, 235), (1888, 235)], LINK, 2.5, dash="5 6")
S.text(1789, 223, "FAILOVER", 11, LINK, 600, anchor="middle", mono=True)

# JetKVM: Ethernet to the Freebox; dashed link represents on-demand console access.
jetkvm = INV["jetkvm"]
endpoint(
    400, 345, 470, 100, jetkvm["name"],
    [f"{jetkvm['type']} · {jetkvm['ip']}", jetkvm["connection"]],
    "glyph-nic", STORAGE
)
S.line([(635, 305), (635, 345)], WAN, SPEED_W["1G"])
S.text(650, 334, INV["network"]["ethernet_speed"], 10.5, WAN, 600, mono=True)
S.rect(970, 345, 720, 100, fill=PANEL2, stroke=MUTED + "88", dash="6 6")
S.text(992, 375, "On-demand HDMI + USB console", 17, TEXT, 600)
S.text(992, 399, jetkvm["console"], 12.5, MUTED, 400)
S.text(992, 421, f"Excludes {jetkvm['excludes']}", 11.5, FAINT, 500)
S.line([(870, 395), (970, 395)], MUTED, 2, dash="6 6")

# MochaBin interfaces. The LAN jacks mirror the physical 2 × 2 layout.
px, py, pw, ph = 42, 470, 2316, 350
mochabin_ports = INV["mochabin"]["ports"]
panel(
    px, py, pw, ph, "MochaBin port map",
    f"eth0 faces left · eth1 empty · eth2 → GS308 · LAN gateway {INV['network']['gateway']}/16"
)
port_box(62, 570, 250, 60, "eth0", mochabin_ports["eth0"], WAN, "SFP+")
port_box(340, 570, 250, 60, "eth1", mochabin_ports["eth1"], FAINT, "SFP+")
port_box(620, 570, 290, 60, "eth2", mochabin_ports["eth2"], CP)
for i, (label, target) in enumerate(
    (("lan0", mochabin_ports["lan0"]), ("lan1", mochabin_ports["lan1"]),
     ("lan2", mochabin_ports["lan2"]), ("lan3", mochabin_ports["lan3"]))
):
    col, row = i % 2, i // 2
    port_box(1020 + col * 330, 570 + row * 70, 300, 60, label, target, STORAGE)

# Server cards and their physical Ethernet paths.
nodes = INV["nodes"]
direct = by_port([n for n in nodes if n["group"] == "MochaBin direct"], r"lan(\d+)")
lan_storage = dict(
    INV["storage"], name=INV["storage"]["name"], role="Storage",
    model=INV["storage"]["model"], connection=INV["storage"]["connection"], storage=True
)
direct.append(lan_storage)
sw_nodes = by_port([n for n in nodes if n["group"] == "GS308"], r"port (\d+)")
node_xs = [42, 642, 1242, 1842]
node_w, node_h = 540, 245
direct_y, switch_y = 900, 1365

direct_links = [
    ([(1170, 570), (1170, 535), (320, 535), (320, direct_y), (312, direct_y)], CP, 330, 700),
    ([(1650, 600), (1810, 600), (1810, direct_y + 122), (1782, direct_y + 122)], CP, 1818, 800),
    ([(1020, 670), (890, 670), (890, 800), (912, 800), (912, direct_y)], CP, 900, 790),
    ([(1650, 670), (1760, 670), (1760, 850), (2112, 850), (2112, direct_y)], STORAGE, 1840, 840),
]
for points, color, label_x, label_y in direct_links:
    S.line(points, color, SPEED_W["1G"])
    S.text(label_x, label_y, INV["network"]["ethernet_speed"], 10.5, color, 600, mono=True)

# GS308 port map. Port 8 is the eth2 uplink; ports 1–4 serve the workers.
sx, sy, sw, sh = 42, 1190, 2316, 100
S.rect(sx, sy, sw, sh, fill=PANEL2, stroke=BORDER, rx=10)
S.text(sx + 18, sy + 30, INV["switch"]["name"], 15, TEXT, 600)
S.text(sx + 18, sy + 51, f"{INV['switch']['uplink']} · 1G uplink", 11, MUTED, 500)
switch_port_x = 280
switch_port_step = 260
switch_port_w = 210
for i, port in enumerate(INV["switch"]["ports"]):
    x = switch_port_x + i * switch_port_step
    color = FAINT if port["to"] == "Free" else CP if "MochaBin" in port["to"] else WORKER
    target = port["to"].split(" · ")[0]
    target = target.replace("HP EliteDesk 800 G6 Mini", "HP Mini 2").replace("IBM dual-Xeon", "IBM")
    S.rect(x, sy + 17, switch_port_w, 60, fill=CHIP, stroke=color + "88", rx=7)
    S.text(x + 10, sy + 37, f"P{port['port']} · {target}", 10.5, color, 600)
    S.text(x + 10, sy + 58, "free" if port["to"] == "Free" else "connected", 10, MUTED, 400)

# Visible 1G cable from eth2 through the gap between the direct nodes to switch port 8.
uplink_x = switch_port_x + 7 * switch_port_step + switch_port_w / 2
S.line([(625, 605), (625, 1160), (uplink_x, 1160), (uplink_x, sy + 17)], CP, SPEED_W["1G"])

for i, node in enumerate(sw_nodes):
    port_number = int(node["connection"].rsplit(" ", 1)[1])
    source_x = switch_port_x + (port_number - 1) * switch_port_step + switch_port_w / 2
    target_x = node_xs[i] + node_w / 2
    S.line([(source_x, sy + 77), (target_x, switch_y)], WORKER, SPEED_W["1G"])
    S.text(source_x + 8, 1318, INV["network"]["ethernet_speed"], 10, WORKER, 600, mono=True)

direct_node_xs = [node_xs[0], node_xs[2], node_xs[1], node_xs[3]]
for i, node in enumerate(direct):
    node_card(node, direct_node_xs[i], direct_y, node_w, node_h)
for i, node in enumerate(sw_nodes):
    node_card(node, node_xs[i], switch_y, node_w, node_h)

# Cilium / VIPs / ingress
bx, by, bw, bh = 42, 1640, 2316, 148
panel(bx, by, bw, bh, "Cilium BGP", f"Talos cluster · {INV['network']['subnet']}", stroke=CP + "88")
vip_width = 740
for i, vip in enumerate(INV["bgp"]["vip_services"]):
    x = bx + 18 + i * 758
    S.rect(x, by + 67, vip_width, 36, fill=CHIP, stroke=BORDER, rx=8)
    S.text(x + 14, by + 90, vip["name"], 13, TEXT, 500)
    S.text(x + vip_width - 14, by + 90, vip["ip"], 13, CP, 600, anchor="end", mono=True)
S.text(bx + 20, by + 131, "Public ingress · TCP 80 / 443 → Traefik VIP", 11.5, LINK, 600)
S.text(
    bx + bw - 20, by + 131,
    "1G Ethernet · 10G SFP+ · dashed = on-demand HDMI/USB",
    11.5, MUTED, 500, "end"
)

OUT.mkdir(exist_ok=True)
name = "homelab-unredacted" if UNREDACTED else "homelab"
svg_path = OUT / f"{name}.svg"
png_path = OUT / f"{name}.png"
svg_path.write_text(S.render())
subprocess.run(["rsvg-convert", "-z", "1.6", "-o", str(png_path), str(svg_path)], check=True)
print(svg_path, png_path)
