"""WiFi Doctor CLI — three read-only commands: speed, channels, devices."""

from __future__ import annotations

import argparse
import sys

from . import channels, devices, speed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wifi-doctor",
        description="Honest, read-only WiFi diagnostics. Nothing here changes your network.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_speed = sub.add_parser("speed", help="Speed test, compared against your plan")
    p_speed.add_argument("--plan", type=float, default=None,
                         help="Your plan's download speed in Mbps (e.g. --plan 500)")

    sub.add_parser("channels", help="Per-channel congestion table + recommendation")

    p_dev = sub.add_parser("devices", help="Inventory of devices on this LAN")
    p_dev.add_argument("--sweep", action="store_true",
                       help="Ping-sweep the local /24 first (read-only, just wakes devices up)")

    args = parser.parse_args(argv)

    try:
        if args.command == "speed":
            result = speed.run_speed_test()
            print(speed.format_speed_report(result, args.plan))
        elif args.command == "channels":
            networks, source = channels.scan_networks()
            print(channels.format_channel_report(networks, source))
        elif args.command == "devices":
            found, swept = devices.inventory(do_sweep=args.sweep)
            print(devices.format_inventory(found, swept=swept))
    except KeyboardInterrupt:
        print("\nStopped. Nothing was changed.", file=sys.stderr)
        return 130
    except Exception as exc:  # never show the user a traceback
        print(f"Something went wrong: {exc}", file=sys.stderr)
        print("Nothing was changed. If it keeps happening, note the command you ran "
              "and the message above.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
