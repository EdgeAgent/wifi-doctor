"""Tests for the speed-vs-plan verdict math and report formatting."""

from wifi_doctor.speed import SpeedResult, format_speed_report, verdict


def test_verdict_healthy():
    v = verdict(450.0, 500.0)
    assert v["label"] == "healthy"
    assert abs(v["ratio"] - 0.9) < 1e-9


def test_verdict_boundary_80_percent_is_healthy():
    assert verdict(400.0, 500.0)["label"] == "healthy"


def test_verdict_below_plan():
    v = verdict(300.0, 500.0)
    assert v["label"] == "below plan"
    assert abs(v["ratio"] - 0.6) < 1e-9


def test_verdict_boundary_50_percent_is_below_not_far():
    assert verdict(250.0, 500.0)["label"] == "below plan"


def test_verdict_far_below_plan():
    assert verdict(100.0, 500.0)["label"] == "far below plan"
    assert verdict(249.0, 500.0)["label"] == "far below plan"


def test_verdict_no_measurement():
    v = verdict(None, 500.0)
    assert v["label"] == "no measurement"
    assert v["ratio"] is None


def test_verdict_no_plan():
    v = verdict(300.0, None)
    assert v["label"] == "no plan given"
    assert v["ratio"] is None
    # A zero/negative plan must not divide-by-zero or produce nonsense.
    assert verdict(300.0, 0)["label"] == "no plan given"


def test_report_with_error_is_plain():
    result = SpeedResult(None, None, None, "timed download", error="Download test failed: boom")
    out = format_speed_report(result, 500.0)
    assert "Could not measure" in out
    assert "Nothing was changed" in out


def test_report_happy_path():
    result = SpeedResult(452.0, 48.0, 12.0, "speedtest-cli (Ookla)")
    out = format_speed_report(result, 500.0)
    assert "452.0 Mbps" in out
    assert "90% of plan" in out
    assert "healthy" in out
