"""WiFi channel congestion: parse a scan, build a per-channel table,
recommend the least-crowded channel.

Input sources, in order: `nmcli -t -f SSID,CHAN,SIGNAL dev wifi list`
(colons inside SSIDs are handled by taking the last two fields), or
`iw dev <iface> scan` output (freq + signal per BSS).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field

NON_OVERLAPPING_24 = (1, 6, 11)
COMMON_5 = (36, 40, 44, 48, 149, 153, 157, 161)


@dataclass
class Network:
    ssid: str
    channel: int
    signal: int  # percent for nmcli, dBm for iw — only compared within one scan
    in_use: bool = False


@dataclass
class ChannelStat:
    channel: int
    count: int = 0
    strongest: int = -999
    load: float = 0.0  # summed signal weight; higher = more crowded
    ssids: list = field(default_factory=list)


def freq_to_channel(freq_mhz: int) -> int | None:
    """Map a centre frequency (MHz) to a WiFi channel number."""
    if freq_mhz == 2484:
        return 14
    if 2412 <= freq_mhz <= 2472:
        return (freq_mhz - 2407) // 5
    if 5000 <= freq_mhz <= 5900:
        return (freq_mhz - 5000) // 5
    if 5955 <= freq_mhz <= 7115:  # 6 GHz
        return (freq_mhz - 5950) // 5
    return None


def parse_nmcli_terse(text: str) -> list[Network]:
    """Parse `nmcli -t -f IN-USE,SSID,CHAN,SIGNAL dev wifi list` output.

    SSIDs may contain ':' so we anchor on the first field (IN-USE) and the
    last two fields (CHAN, SIGNAL) and treat the middle as the SSID.
    """
    networks = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.replace("\\:", "\x00").split(":")
        if len(parts) < 4:
            continue
        in_use = parts[0] == "*"
        try:
            chan = int(parts[-2])
            signal = int(parts[-1])
        except ValueError:
            continue
        ssid = ":".join(parts[1:-2]).replace("\x00", ":")
        networks.append(Network(ssid=ssid, channel=chan, signal=signal, in_use=in_use))
    return networks


def parse_iw_scan(text: str) -> list[Network]:
    """Parse `iw dev <iface> scan` output into networks (SSID best-effort)."""
    networks = []
    current: dict = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("BSS "):
            if "freq" in current:
                ch = freq_to_channel(current["freq"])
                if ch:
                    networks.append(Network(
                        ssid=current.get("ssid", "(hidden)"),
                        channel=ch,
                        signal=current.get("signal", -100),
                    ))
            current = {}
        elif line.startswith("freq:"):
            try:
                current["freq"] = int(float(line.split(":", 1)[1].strip()))
            except ValueError:
                pass
        elif line.startswith("signal:"):
            try:
                current["signal"] = int(float(line.split(":", 1)[1].split()[0]))
            except ValueError:
                pass
        elif line.startswith("SSID:"):
            current["ssid"] = line.split(":", 1)[1].strip() or "(hidden)"
    if "freq" in current:
        ch = freq_to_channel(current["freq"])
        if ch:
            networks.append(Network(
                ssid=current.get("ssid", "(hidden)"),
                channel=ch,
                signal=current.get("signal", -100),
            ))
    return networks


def congestion_table(networks: list[Network]) -> dict[int, ChannelStat]:
    """Group networks by channel with a simple crowding load.

    Load weights stronger networks more heavily (a -40 dBm neighbour hurts
    more than a -90 dBm one). Signals are normalised so both percent
    (nmcli) and dBm (iw) scans produce comparable *relative* loads.
    """
    table: dict[int, ChannelStat] = {}
    if not networks:
        return table
    top = max(n.signal for n in networks)
    for n in networks:
        stat = table.setdefault(n.channel, ChannelStat(channel=n.channel))
        stat.count += 1
        stat.strongest = max(stat.strongest, n.signal)
        stat.load += max(0.05, 1.0 - (top - n.signal) / 60.0)
        if n.ssid and n.ssid not in stat.ssids:
            stat.ssids.append(n.ssid)
    return table


def recommend_channel(networks: list[Network]) -> dict:
    """Recommend the least-crowded channel for each band present in the scan.

    2.4 GHz recommendation is restricted to the non-overlapping 1/6/11.
    """
    table = congestion_table(networks)
    rec: dict = {"table": table}

    def load_with_overlap(ch: int, width: int = 2) -> float:
        # Neighbouring 2.4 GHz channels overlap; count their load at half weight.
        total = 0.0
        for other, stat in table.items():
            if other == ch:
                total += stat.load
            elif abs(other - ch) <= width and other < 15:
                total += stat.load * 0.5
        return total

    if any(n.channel < 15 for n in networks):
        best24 = min(NON_OVERLAPPING_24, key=load_with_overlap)
        rec["2.4GHz"] = {"channel": best24, "load": round(load_with_overlap(best24), 2)}
    chans5 = sorted({n.channel for n in networks if 15 < n.channel < 200})
    if chans5:
        candidates = sorted(set(COMMON_5) | set(chans5))
        best5 = min(candidates, key=lambda c: table.get(c, ChannelStat(c)).load)
        rec["5GHz"] = {"channel": best5, "load": round(table.get(best5, ChannelStat(best5)).load, 2)}
    mine = [n for n in networks if n.in_use]
    if mine:
        rec["current"] = mine[0].channel
    return rec


def scan_networks() -> tuple[list[Network], str]:
    """Run a live scan. Returns (networks, source-description)."""
    if shutil.which("nmcli"):
        proc = subprocess.run(
            ["nmcli", "-t", "-f", "IN-USE,SSID,CHAN,SIGNAL", "dev", "wifi", "list", "--rescan", "auto"],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return parse_nmcli_terse(proc.stdout), "nmcli"
    if shutil.which("iw"):
        devs = subprocess.run(["iw", "dev"], capture_output=True, text=True, timeout=15)
        m = re.search(r"Interface\s+(\S+)", devs.stdout)
        if m:
            proc = subprocess.run(
                ["iw", "dev", m.group(1), "scan"], capture_output=True, text=True, timeout=60,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return parse_iw_scan(proc.stdout), "iw scan"
    return [], "none"


def format_channel_report(networks: list[Network], source: str) -> str:
    if not networks:
        return (
            "WiFi Doctor — channels\n"
            "No WiFi scan available in this environment (no nmcli/iw scan results — "
            "this machine may have no WiFi adapter, or the scan tools are not installed).\n"
            "Nothing was changed. On your own machine, the prompts in prompts/ walk through this step."
        )
    rec = recommend_channel(networks)
    table = rec["table"]
    lines = [f"WiFi Doctor — channel congestion  (source: {source}, {len(networks)} networks seen)", ""]
    lines.append(f"{'CH':>4}  {'NETWORKS':>8}  {'LOAD':>5}  NETWORKS")
    for ch in sorted(table):
        stat = table[ch]
        names = ", ".join(stat.ssids[:4]) + ("…" if len(stat.ssids) > 4 else "")
        lines.append(f"{ch:>4}  {stat.count:>8}  {stat.load:>5.1f}  {names}")
    lines.append("")
    if "current" in rec:
        lines.append(f"Your network is on channel {rec['current']}.")
    if "2.4GHz" in rec:
        lines.append(f"Least crowded 2.4 GHz channel: {rec['2.4GHz']['channel']} (of 1/6/11, the non-overlapping set)")
    if "5GHz" in rec:
        lines.append(f"Least crowded 5 GHz channel: {rec['5GHz']['channel']}")
    lines.append("")
    lines.append("Moving channels is a router-admin change — this tool will not do it.")
    lines.append("See prompts/prompt-1-speed-doctor.md, Step 5: the exact change is shown")
    lines.append("and applied only with your explicit OK.")
    return "\n".join(lines)
