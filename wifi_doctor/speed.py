"""Speed test + speed-vs-plan verdict.

Two methods, always labelled in the output:
  1. speedtest-cli, if it happens to be installed.
  2. Fallback: a timed HTTPS download of a known-size test file
     (Cloudflare's speed-test endpoint). This measures download only.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import urllib.request
from dataclasses import dataclass

TEST_URL = "https://speed.cloudflare.com/__down?bytes=25000000"  # 25 MB
TEST_BYTES = 25_000_000


@dataclass
class SpeedResult:
    download_mbps: float | None
    upload_mbps: float | None
    ping_ms: float | None
    method: str
    error: str | None = None


def verdict(download_mbps: float | None, plan_mbps: float | None) -> dict:
    """Compare a measured download speed against the plan.

    Returns a dict with ratio (or None) and a plain-English label.
    Thresholds: >=80% healthy, 50-80% below plan, <50% far below plan.
    """
    if download_mbps is None:
        return {"ratio": None, "label": "no measurement", "detail": "The speed test did not produce a number."}
    if not plan_mbps or plan_mbps <= 0:
        return {
            "ratio": None,
            "label": "no plan given",
            "detail": "Re-run with --plan <Mbps> to compare against what you pay for.",
        }
    ratio = download_mbps / plan_mbps
    if ratio >= 0.8:
        label = "healthy"
        detail = "You are getting at least 80% of your plan speed on this device, right now."
    elif ratio >= 0.5:
        label = "below plan"
        detail = "You are getting 50-80% of your plan speed. Channel congestion or a background hog is worth checking."
    else:
        label = "far below plan"
        detail = "You are getting under half your plan speed. Work through `channels` and `devices`, then the fix list in prompts/prompt-1-speed-doctor.md."
    return {"ratio": ratio, "label": label, "detail": detail}


def _via_speedtest_cli() -> SpeedResult | None:
    exe = shutil.which("speedtest-cli") or shutil.which("speedtest")
    if not exe:
        return None
    try:
        proc = subprocess.run(
            [exe, "--json"], capture_output=True, text=True, timeout=120,
        )
        data = json.loads(proc.stdout)
        return SpeedResult(
            download_mbps=data["download"] / 1_000_000,
            upload_mbps=data["upload"] / 1_000_000,
            ping_ms=data.get("ping"),
            method="speedtest-cli (Ookla)",
        )
    except Exception as exc:  # fall through to the download method
        return SpeedResult(None, None, None, "speedtest-cli", error=f"speedtest-cli failed: {exc}")


def _via_timed_download() -> SpeedResult:
    try:
        req = urllib.request.Request(TEST_URL, headers={"User-Agent": "wifi-doctor/0.1"})
        start = time.monotonic()
        total = 0
        with urllib.request.urlopen(req, timeout=60) as resp:
            while True:
                chunk = resp.read(262_144)
                if not chunk:
                    break
                total += len(chunk)
        elapsed = time.monotonic() - start
        if elapsed <= 0 or total == 0:
            return SpeedResult(None, None, None, "timed download", error="Download returned no data.")
        mbps = (total * 8) / elapsed / 1_000_000
        return SpeedResult(mbps, None, None, f"timed download of {total / 1_000_000:.0f} MB from Cloudflare")
    except Exception as exc:
        return SpeedResult(None, None, None, "timed download", error=f"Download test failed: {exc}")


def run_speed_test() -> SpeedResult:
    result = _via_speedtest_cli()
    if result is not None and result.download_mbps is not None:
        return result
    return _via_timed_download()


def format_speed_report(result: SpeedResult, plan_mbps: float | None) -> str:
    lines = ["WiFi Doctor — speed test", f"Method: {result.method}"]
    if result.error:
        lines.append(f"Could not measure: {result.error}")
        lines.append("Check your internet connection and try again. Nothing was changed.")
        return "\n".join(lines)
    if result.download_mbps is not None:
        lines.append(f"Download: {result.download_mbps:.1f} Mbps")
    if result.upload_mbps is not None:
        lines.append(f"Upload:   {result.upload_mbps:.1f} Mbps")
    if result.ping_ms is not None:
        lines.append(f"Ping:     {result.ping_ms:.0f} ms")
    v = verdict(result.download_mbps, plan_mbps)
    if v["ratio"] is not None:
        lines.append(f"Plan:     {plan_mbps:.0f} Mbps  ({v['ratio'] * 100:.0f}% of plan)")
    lines.append(f"Verdict:  {v['label']} — {v['detail']}")
    lines.append("")
    lines.append("Note: a speed test measures this device, right now. A slow result can be")
    lines.append("the device, the distance to the router, or the connection itself.")
    return "\n".join(lines)
