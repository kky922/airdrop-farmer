import json

import pytest

import main


ADDRESS = "0x0000000000000000000000000000000000000000"


def test_estimate_cost():
    assert main.estimate_cost(12, 0.08) == 0.96


def test_estimate_cost_rejects_negative_values():
    with pytest.raises(ValueError):
        main.estimate_cost(-1, 0.1)


def test_eligibility_uses_public_activity_thresholds():
    result = main.check_eligibility(ADDRESS, transactions=12, unique_days=6)
    assert result.eligible is True
    assert result.reasons == []


def test_eligibility_rejects_invalid_address():
    with pytest.raises(ValueError):
        main.check_eligibility("not-an-address", 12, 6)


def test_report_is_read_only_and_serializable():
    report = main.build_report(ADDRESS, transactions=12, unique_days=6, fee_usd=0.08)
    assert report["mode"] == "read-only"
    assert "private_key" not in json.dumps(report)
