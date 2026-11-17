"""Tests for device inventory parsing, vendor lookup, and formatting."""

from wifi_doctor.devices import (
    Device,
    format_inventory,
    parse_ip_neigh,
    parse_proc_arp,
)
from wifi_doctor.oui import vendor_for_mac

IP_NEIGH_FIXTURE = """\
192.168.1.1 dev eth0 lladdr 50:c7:bf:aa:bb:cc REACHABLE
192.168.1.42 dev eth0 lladdr b8:27:eb:11:22:33 STALE
192.168.1.77 dev eth0 lladdr 18:fe:34:44:55:66 DELAY
192.168.1.99 dev eth0 FAILED
fe80::1 dev eth0 lladdr 50:c7:bf:aa:bb:cc router REACHABLE
"""

PROC_ARP_FIXTURE = """\
IP address       HW type     Flags       HW address            Mask     Device
192.168.1.1      0x1         0x2         50:c7:bf:aa:bb:cc     *        eth0
192.168.1.50     0x1         0x0         00:00:00:00:00:00     *        eth0
"""


def test_parse_ip_neigh():
    devices = parse_ip_neigh(IP_NEIGH_FIXTURE)
    ips = [d.ip for d in devices]
    assert ips == ["192.168.1.1", "192.168.1.42", "192.168.1.77"]
    # The FAILED entry (no MAC, no device) must be excluded.
    assert "192.168.1.99" not in ips


def test_parse_proc_arp():
    devices = parse_proc_arp(PROC_ARP_FIXTURE)
    assert len(devices) == 1  # the all-zero MAC row is not a real device
    assert devices[0].ip == "192.168.1.1"


def test_vendor_lookup():
    assert vendor_for_mac("50:c7:bf:aa:bb:cc") == "TP-Link"
    assert vendor_for_mac("B8:27:EB:11:22:33") == "Raspberry Pi"  # case-insensitive
    assert vendor_for_mac("18:fe:34:44:55:66") == "Espressif (IoT)"
    assert vendor_for_mac("02:11:22:33:44:55") is None  # locally administered / not in sample
    assert vendor_for_mac(None) is None
    assert vendor_for_mac("") is None


def test_device_vendor_property():
    assert Device(ip="192.168.1.1", mac="50:c7:bf:aa:bb:cc").vendor == "TP-Link"
    assert Device(ip="192.168.1.2", mac="02:aa:bb:cc:dd:ee").vendor == "unknown vendor"
    assert Device(ip="192.168.1.3", mac=None).vendor == "unknown vendor"


def test_format_inventory_contents():
    devices = parse_ip_neigh(IP_NEIGH_FIXTURE)
    out = format_inventory(devices)
    assert "192.168.1.1" in out
    assert "TP-Link" in out
    assert "Raspberry Pi" in out
    assert "3 device(s)" in out
    # The honesty notes must be there: read-only, blocking is at the router.
    assert "read-only" in out
    assert "ROUTER" in out


def test_format_inventory_empty():
    out = format_inventory([])
    assert "No devices found" in out
