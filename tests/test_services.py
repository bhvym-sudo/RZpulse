import csv
import json
import stat

import pytest

from rzpulse.services.analytics import summarize
from rzpulse.services.export import export_records
from rzpulse.utils.formatting import money, timestamp
from rzpulse.utils.security import redact


def test_redaction_nested_and_original_unchanged():
    data = {"id": "pay_1", "notes": {"x": "private"}, "items": [
        {"email": "private", "other": "contains unit-secret"}]}
    safe = redact(data, ("unit-secret",))
    assert "private" not in json.dumps(safe)
    assert "unit-secret" not in json.dumps(safe)
    assert data["notes"]["x"] == "private"
    assert safe["id"] == "pay_1"


@pytest.mark.parametrize("amount,currency,result", [
    (12345, "INR", "INR 123.45"), (100, "JPY", "JPY 100"),
    (1234, "KWD", "KWD 1.234"), (None, "INR", "—"),
    (1234, "ZZZ", "ZZZ 1,234 subunits"), (0, "USD", "USD 0.00"),
])
def test_money(amount, currency, result):
    assert money(amount, currency) == result


def test_timestamp():
    assert timestamp(None) == "—"
    assert timestamp(1700000000) == "2023-11-14 22:13 UTC"


def test_analytics_no_currency_mixing():
    stats = summarize([{"status": "captured", "amount": 100, "currency": "INR"},
                       {"status": "captured", "amount": 200, "currency": "USD"},
                       {"status": "authorized", "amount": 300, "currency": "INR"},
                       {"status": "failed"}, {}])
    assert stats == {"payments": 5, "successful": 2, "failed": 1,
                     "captured": {"INR": 100, "USD": 200}}
    assert summarize([])["payments"] == 0


def test_exports(tmp_path):
    records = [{"id": "=danger", "email": "private", "other": "unit-secret"}]
    path = tmp_path / "page.json"
    export_records(path, records, ("unit-secret",))
    assert "private" not in path.read_text() and "unit-secret" not in path.read_text()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        export_records(path, [])
    path = tmp_path / "page.csv"
    export_records(path, records)
    with path.open() as f:
        assert list(csv.DictReader(f))[0]["id"] == "'=danger"


def test_refund_summary_only_processed():
    from rzpulse.services.analytics import refund_summary
    assert refund_summary([
        {"status": "processed", "amount": 100, "currency": "INR"},
        {"status": "pending", "amount": 200, "currency": "INR"},
        {"status": "failed", "amount": 300, "currency": "USD"},
    ]) == {"count": 3, "processed": 1, "amounts": {"INR": 100}}


def test_csv_hostile_header_and_whitespace(tmp_path):
    path = tmp_path / "safe.csv"
    export_records(path, [{"=key": "  =formula", "id": "\n=another"}])
    with path.open() as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["'=key", "id"]
    assert all(value.startswith("'") for value in rows[1])
