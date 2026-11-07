# CLAUDE.md – this homelab diagram

This fork describes a Freebox Ultra, MochaBin 5G router, and Talos Kubernetes homelab. Keep `inventory.yaml` and the hand-placed layout in `build.py` synchronized when changing the topology.

Start by telling the user briefly how this works (interview → inventory → layout → render/feedback rounds), then begin the interview. Don't ask everything at once.

## How the repo works

- `inventory.yaml` – topology, IP assignments, router and switch ports, Talos nodes, BGP VIPs, ingress ports, and storage devices.
- `build.py` – draws the hand-placed SVG layout (logical canvas `W = 2400`, `H = 1460`), embeds icons as base64, and converts it to PNG with `rsvg-convert -z 1.6`.
- `icons/glyph-*.svg` – local hardware icons used by this diagram; no icon download is needed.
- Output: `out/homelab.png` and `out/homelab.svg`. The diagram contains private network addresses; `--unredacted` only writes a second copy with an `-unredacted` filename.

### Inventory and layout

Inventory-driven content includes device models and addresses, router and switch port targets, node roles and specifications, VIPs, ingress ports, and storage devices. Layout and card positions are hand-placed in `build.py`:

| Section (search for) | What's fixed | Typical change |
|---|---|---|
| `# Internet edge` | ISP, router, and 5G failover card positions | move or resize WAN devices |
| `# MochaBin port map` | `eth0`/`eth1` SFP+ badges, `eth2`, and `lan0`–`lan3` positions | adjust port layout or target labels |
| `# Cilium / VIPs / ingress` | VIP list and ingress panel | add or remove cluster services |
| `# Kubernetes nodes` | two four-card rows and their spacing | add nodes or rearrange connection groups |
| `# Switch port map` | eight compact port cards | change switch size or port labels |
| `W, H` | SVG canvas size | grow the canvas when content gets taller |

Always inspect the rendered image for clipped text, overlap, and excess whitespace.

## The interview

Ask in rounds of 3–6 questions, grouped by topic, and offer defaults. If the user has documentation (wiki, notes, a docs repo) or you have shell access to their systems, offer to read that first and only ask for the gaps. **Only run read-only commands, and ask before touching any system.**

1. **Purpose & privacy:** public post (e.g. Reddit) or private? Real domain to hide? Real SSID names to hide? Username watermark? Title and date?
2. **Internet edge:** ISP connection type and speed (down/up), modem/router model, its ports and which one the firewall uses, bridge mode or double NAT/exposed host, DNS provider, offsite backup target.
3. **Firewall/router:** hardware (CPU, RAM, NICs), OS + version, management IP/hostname, services (DNS, DHCP, VPN, IDS/IPS, …), LACP/bonds.
4. **Switch(es):** model, OS/version, management IP, and per port: connected device, negotiated speed, untagged VLAN, tagged VLANs. (Many switches can print this, e.g. RouterOS `/interface ethernet monitor [find] once` and `/interface bridge vlan print`.)
5. **VLANs:** ID, name, subnet, one-line policy ("internet only", "services, no LAN access", …). Colors: keep the defaults unless they want others.
6. **Other devices:** workstation(s), KVM, access points (SSIDs → VLANs), IoT radios/coordinators, NAS boxes, anything with a cable.
7. **Server(s):** hypervisor + version, CPU, RAM, GPU, NICs, every disk (model/size) and whether it's passed through to a VM.
8. **Guests:** every VM/container: ID, IP, VLAN, what runs in it. Containers running several apps (often Docker) become one card with a row per app. Which apps are public (behind a reverse proxy, shown as `app.domain`), which LAN-only, which have no web UI (`name.internal`)?
9. **Storage:** pools/vdevs/disks, used/free, shares and who mounts them.
10. **Port forwards:** port, protocol, target, purpose.
11. **Extras:** remote access/VPN, cloud services, a flow worth explaining (like the media pipeline), anything they're proud of or want to highlight.

Useful read-only commands if you have access (ask first): Proxmox `pct list`, `qm list`, `pct config <id>`; `docker ps`; `ip -br a`; ZFS `zpool list -v`, `zfs list`; TrueNAS `midclt call pool.query`, `midclt call disk.query`; `lspci`; `lsblk -o NAME,MODEL,SIZE`.

## The work loop

1. Write `inventory.yaml` for their lab (keep the schema; extend it when needed and teach `build.py` the new fields).
2. Adapt `build.py`: decide which panels exist and adjust the hand-placed positions above.
3. Use a local `glyph-*.svg` icon or add an SVG to `icons/` and reference its filename.
4. `python3 build.py`, then **look at `out/homelab.png` yourself** before showing it. Zoom into busy areas: `magick out/homelab.png -crop 1400x600+X+Y +repage -resize 70% /tmp/crop.png` (X/Y in PNG pixels = SVG coordinates × 1.6). Look for overlapping text, cables crossing cards, text running out of boxes, empty gaps.
5. Show the user, take feedback, change, re-render. Expect many small rounds, that's normal.
6. This fork's default render includes private IP addresses. Before public sharing, redact private identifiers in the inventory and inspect the generated SVG and PNG.

## Design rules (keep them unless the user wants otherwise)

- The Freebox link is primary; MochaBin 5G is failover.
- Keep the MochaBin SFP and 2×2 LAN port targets synchronized with the node connection labels.
- Use role colors for control planes, workers, and the separate storage appliance.
- Show BGP VIPs and only the public HTTP/HTTPS ingress ports.
- Keep hardware and storage details plain and concise.
- Keep text plain and short; no marketing-style subtitles.

## Gotchas

- Fonts: **Fira Sans** and **Fira Code** should be installed for consistent rendering.
- When content grows, grow `H` or adjust the affected panel and card positions.
