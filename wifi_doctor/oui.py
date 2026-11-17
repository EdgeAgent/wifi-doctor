"""A small built-in sample of MAC OUI (vendor) prefixes.

This is deliberately a *sample* — a few dozen common consumer vendors — not
the full IEEE registry. A miss returns None and the report says "unknown
vendor" rather than guessing. Prefixes are the first 3 bytes, uppercase,
colon-separated.
"""

OUI_SAMPLE = {
    # Apple
    "00:1B:63": "Apple", "00:1C:B3": "Apple", "00:23:32": "Apple",
    "3C:07:54": "Apple", "A4:B1:97": "Apple", "F0:D1:A9": "Apple",
    "28:CF:E9": "Apple", "BC:52:B7": "Apple",
    # Samsung
    "00:12:FB": "Samsung", "5C:3C:27": "Samsung", "78:25:AD": "Samsung",
    "8C:71:F8": "Samsung", "BC:44:86": "Samsung",
    # Google / Nest
    "18:B4:30": "Google Nest", "54:60:09": "Google", "F4:F5:D8": "Google",
    "D8:A0:1D": "Google",
    # Amazon (Echo / Fire / Ring)
    "44:65:0D": "Amazon", "68:54:FD": "Amazon", "A0:02:DC": "Amazon",
    "FC:A1:83": "Amazon", "74:C2:46": "Amazon",
    # Microsoft
    "00:50:F2": "Microsoft", "28:18:78": "Microsoft", "7C:1E:52": "Microsoft",
    # Sony
    "00:04:1F": "Sony", "78:84:3C": "Sony", "AC:9B:0A": "Sony",
    # LG
    "00:1C:62": "LG", "A8:23:FE": "LG", "10:68:3F": "LG",
    # TP-Link
    "50:C7:BF": "TP-Link", "A4:2B:B0": "TP-Link", "1C:3B:AD": "TP-Link",
    # Netgear
    "00:14:6C": "Netgear", "20:E5:2A": "Netgear", "9C:3D:CF": "Netgear",
    # ASUS
    "00:1A:92": "ASUS", "2C:FD:A1": "ASUS", "04:D4:C4": "ASUS",
    # D-Link
    "00:05:5D": "D-Link", "1C:7E:E5": "D-Link",
    # Linksys / Belkin
    "00:06:25": "Linksys", "48:F8:B3": "Belkin",
    # Intel (laptop WiFi cards)
    "00:13:E8": "Intel", "3C:F0:11": "Intel", "9C:DA:3E": "Intel",
    "34:13:E8": "Intel",
    # Raspberry Pi
    "B8:27:EB": "Raspberry Pi", "DC:A6:32": "Raspberry Pi", "E4:5F:01": "Raspberry Pi",
    # Espressif (ESP8266/ESP32 — smart plugs, IoT gadgets)
    "18:FE:34": "Espressif (IoT)", "24:0A:C4": "Espressif (IoT)",
    "7C:9E:BD": "Espressif (IoT)", "8C:AA:B5": "Espressif (IoT)",
    # Tuya / smart-home
    "D8:A0:1D": "Google", "38:2B:78": "Tuya (smart home)",
    # Roku
    "B0:A7:37": "Roku", "D8:31:34": "Roku",
    # HP / printers
    "00:1B:78": "HP", "3C:D9:2B": "HP",
    # Huawei / Xiaomi
    "00:E0:FC": "Huawei", "28:6E:D4": "Xiaomi", "64:CC:2E": "Xiaomi",
    # Philips Hue / Signify
    "00:17:88": "Philips Hue", "EC:B5:FA": "Philips Hue",
    # Sonos
    "00:0E:58": "Sonos", "48:A6:B8": "Sonos",
    # Ubiquiti
    "00:27:22": "Ubiquiti", "24:A4:3C": "Ubiquiti", "F0:9F:C2": "Ubiquiti",
    # Cisco
    "00:00:0C": "Cisco", "58:97:1E": "Cisco",
    # Nintendo
    "00:09:BF": "Nintendo", "7C:BB:8A": "Nintendo",
    # Virtualisation (useful to flag, not a physical device)
    "00:50:56": "VMware (virtual)", "08:00:27": "VirtualBox (virtual)",
    "52:54:00": "QEMU/KVM (virtual)",
}


def vendor_for_mac(mac: str | None) -> str | None:
    """Look up the vendor for a MAC address in the built-in sample."""
    if not mac:
        return None
    prefix = mac.upper().replace("-", ":")[:8]
    return OUI_SAMPLE.get(prefix)
