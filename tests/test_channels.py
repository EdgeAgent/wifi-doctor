"""Tests for channel parsing, congestion table, and recommendation."""

from wifi_doctor.channels import (
    congestion_table,
    freq_to_channel,
    parse_iw_scan,
    parse_nmcli_terse,
    recommend_channel,
)

NMCLI_FIXTURE = """\
*:HomeNet:6:72
:NeighbourNet:6:65
:PrinterNet:6:30
:CoffeeDownstairs:1:40
:FarAway:1:20
:Upstairs:11:55
:FiveGHome:36:80
:FiveGNeighbour:36:45
"""

IW_FIXTURE = """\
BSS aa:bb:cc:dd:ee:ff(on wlan0)
\tfreq: 2437
\tsignal: -52.00 dBm
\tSSID: HomeNet
BSS 11:22:33:44:55:66(on wlan0)
\tfreq: 5180
\tsignal: -61.00 dBm
\tSSID: FiveGHome
BSS 77:88:99:aa:bb:cc(on wlan0)
\tfreq: 2412
\tsignal: -80.00 dBm
\tSSID: WeakOne
"""


def test_freq_to_channel():
    assert freq_to_channel(2412) == 1
    assert freq_to_channel(2437) == 6
    assert freq_to_channel(2462) == 11
    assert freq_to_channel(2484) == 14
    assert freq_to_channel(5180) == 36
    assert freq_to_channel(5745) == 149
    assert freq_to_channel(900) is None


def test_parse_nmcli_terse():
    nets = parse_nmcli_terse(NMCLI_FIXTURE)
    assert len(nets) == 8
    mine = [n for n in nets if n.in_use]
    assert len(mine) == 1 and mine[0].ssid == "HomeNet" and mine[0].channel == 6


def test_parse_nmcli_ssid_with_colon():
    nets = parse_nmcli_terse(":Weird:Name:6:50\n")
    assert len(nets) == 1
    assert nets[0].ssid == "Weird:Name"
    assert nets[0].channel == 6


def test_parse_iw_scan():
    nets = parse_iw_scan(IW_FIXTURE)
    assert len(nets) == 3
    by_ssid = {n.ssid: n for n in nets}
    assert by_ssid["HomeNet"].channel == 6
    assert by_ssid["FiveGHome"].channel == 36
    assert by_ssid["WeakOne"].channel == 1


def test_congestion_table_counts():
    nets = parse_nmcli_terse(NMCLI_FIXTURE)
    table = congestion_table(nets)
    assert table[6].count == 3
    assert table[1].count == 2
    assert table[36].count == 2
    # Channel 6 carries the strongest neighbour load in this fixture.
    assert table[6].load > table[11].load


def test_recommendation_avoids_crowded_channel():
    nets = parse_nmcli_terse(NMCLI_FIXTURE)
    rec = recommend_channel(nets)
    assert rec["current"] == 6
    # 6 is the crowded one; the pick must be one of the non-overlapping set, not 6.
    assert rec["2.4GHz"]["channel"] in (1, 11)
    # 5 GHz: only channel 36 is in use in the fixture; a clear common channel wins.
    assert rec["5GHz"]["channel"] != 36 or rec["5GHz"]["load"] == 0


def test_empty_scan():
    assert congestion_table([]) == {}
    rec = recommend_channel([])
    assert "2.4GHz" not in rec and "5GHz" not in rec
