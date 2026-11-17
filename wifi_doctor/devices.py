"""LAN device inventory: ARP/neighbour table + optional ping sweep.

Read-only. Finds devices; never blocks, kicks, or changes anything.
Blocking lives at the router — see prompts/prompt-2-device-audit.md.
"""

from __future__ import annotations

import re
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from .oui import vendor_for_mac


@dataclass
class Device:
    ip: str
    mac: str | None
    state: str = ""
    hostname: str | None = None

    @property
    def vendor(self) -> str:
        return vendor_for_mac(self.mac) or "unknown vendor"


_IP_NEIGH_RE = re.compile(
    r"^(?P<ip>\d+\.\d+\.\d+\.\d+)\s+(?:dev\s+\S+\s+)?"
    r"(?:lladdr\s+(?P<mac>[0-9a-fA-F:]{17})\s+)?(?P<rest>.*)$"
)


def parse_ip_neigh(text: str) -> list[Device]:
    """Parse `ip neigh show` output."""
    devices = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _IP_NEIGH_RE.match(line)
        if not m:
            continue
        rest = m.group("rest") or ""
        state = rest.split()[-1] if rest.split() else ""
        if m.group("mac") is None and "FAILED" in rest.upper():
            continue  # incomplete ARP entry, no device really there
        devices.append(Device(ip=m.group("ip"), mac=m.group("mac"), state=state))
    return devices


def parse_proc_arp(text: str) -> list[Device]:
    """Parse /proc/net/arp content (fallback when `ip` is unavailable)."""
    devices = []
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 4 and parts[3] != "00:00:00:00:00:00":
            devices.append(Device(ip=parts[0], mac=parts[3]))
    return devices


def read_arp_table() -> list[Device]:
    try:
        proc = subprocess.run(
            ["ip", "neigh", "show"], capture_output=True, text=True, timeout=15,
        )
        if proc.returncode == 0:
            return parse_ip_neigh(proc.stdout)
    except Exception:
        pass
    try:
        with open("/proc/net/arp", encoding="utf-8") as fh:
            return parse_proc_arp(fh.read())
    except OSError:
        return []


def local_subnet() -> str | None:
    """Best-effort /24 of this machine's primary LAN address."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))  # no traffic is actually sent (UDP)
            ip = sock.getsockname()[0]
        finally:
            sock.close()
        if ip.startswith(("10.", "192.168.", "172.")):
            return ".".join(ip.split(".")[:3]) + ".0/24"
    except OSError:
        pass
    return None


def _ping(ip: str) -> bool:
    try:
        proc = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip],
            capture_output=True, timeout=3,
        )
        return proc.returncode == 0
    except Exception:
        return False


def ping_sweep(subnet: str) -> int:
    """Ping every host in a /24 to populate the ARP table. Returns replies."""
    base = subnet.split("/")[0].rsplit(".", 1)[0]
    hosts = [f"{base}.{i}" for i in range(1, 255)]
    alive = 0
    with ThreadPoolExecutor(max_workers=32) as pool:
        for ok in pool.map(_ping, hosts):
            alive += 1 if ok else 0
    return alive


def try_hostname(ip: str) -> str | None:
    try:
        name = socket.gethostbyaddr(ip)[0]
        return None if name == ip else name
    except (socket.herror, OSError):
        return None


def inventory(do_sweep: bool = False) -> tuple[list[Device], bool]:
    """Returns (devices, sweep_actually_ran)."""
    swept = False
    if do_sweep:
        subnet = local_subnet()
        if subnet:
            ping_sweep(subnet)
            swept = True
    devices = read_arp_table()
    for d in devices:
        d.hostname = try_hostname(d.ip)
    devices.sort(key=lambda d: tuple(int(p) for p in d.ip.split(".")))
    return devices, swept


def format_inventory(devices: list[Device], swept: bool = False) -> str:
    lines = ["WiFi Doctor — devices on this network"]
    if swept:
        lines.append("(ping sweep ran first, so sleepy devices had a chance to answer)")
    if not devices:
        lines.append("No devices found in the ARP table.")
        lines.append("That usually means this machine is not on a home LAN, or the table is")
        lines.append("empty. Try again with:  python3 -m wifi_doctor devices --sweep")
        return "\n".join(lines)
    lines.append("")
    lines.append(f"{'#':>3}  {'IP':<15}  {'MAC':<17}  {'VENDOR':<22}  HOSTNAME")
    for i, d in enumerate(devices, 1):
        lines.append(
            f"{i:>3}  {d.ip:<15}  {(d.mac or '—'):<17}  {d.vendor:<22}  {d.hostname or '—'}"
        )
    lines.append("")
    lines.append(f"{len(devices)} device(s). Vendor names come from a small built-in sample")
    lines.append("of MAC prefixes — 'unknown vendor' means 'not in the sample', not 'intruder'.")
    lines.append("A device that is asleep or ignoring pings may not appear at all.")
    lines.append("")
    lines.append("See something you don't recognize? Blocking happens at your ROUTER")
    lines.append("(MAC filter / device block in the admin page) — this tool is read-only")
    lines.append("and will not do it. prompts/prompt-2-device-audit.md walks you through")
    lines.append("it, one device at a time, with your OK for each — and how to undo it.")
    return "\n".join(lines)
