"""Headless integration tests; no real network or credentials."""
import asyncio

import httpx
import pytest

pytest.importorskip("textual", reason="Textual dependency is required for headless TUI checks")
from textual.widgets import DataTable, Input, Select  # noqa: E402
from rzpulse.api.client import RazorpayClient  # noqa: E402
from rzpulse.app import Detail, RZPulse  # noqa: E402


def test_unconfigured_launch_and_help(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    async def scenario():
        app = RZPulse()
        async with app.run_test(size=(120, 40)) as pilot:
            assert app.section == "settings"
            await pilot.press("question_mark")
            assert isinstance(app.screen, Detail)
            await pilot.press("escape")
            await app.navigate("payments")
            await pilot.pause()
            assert app.query_one("#table", DataTable).row_count == 0
            app.query_one("#search", Input).focus()
            await pilot.press("q", "r", "j")
            assert app.query_one("#search", Input).value == "qrj"
    asyncio.run(scenario())


def test_resource_pagination_detail_explorer(settings):
    calls = []
    def handler(request):
        calls.append(request)
        row = {"id": "pay_abc", "amount": 100, "currency": "INR", "status": "captured",
               "email": "private@example.test", "created_at": 1700000000}
        if request.url.path.endswith("/pay_abc"):
            return httpx.Response(200, json=row)
        rows = [dict(row, id=f"pay_{i}") for i in range(25)] if request.url.params.get("skip") == "0" else []
        return httpx.Response(200, json={"count": len(rows), "items": rows})
    async def scenario():
        client = RazorpayClient(settings, transport=httpx.MockTransport(handler))
        app = RZPulse(settings, client)
        async with app.run_test(size=(120, 50)) as pilot:
            await app.workers.wait_for_complete()
            await app.navigate("payments")
            await app.workers.wait_for_complete()
            assert app.query_one("#table", DataTable).row_count == 25
            app.show_record("pay_abc")
            await app.workers.wait_for_complete()
            assert isinstance(app.screen, Detail)
            assert app.screen.data["email"] == "[REDACTED]"
            await pilot.press("escape")
            await pilot.click("#next")
            await app.workers.wait_for_complete()
            assert app.skip == 25
            assert app.query_one("#table", DataTable).row_count == 0
            for resource in ("orders", "refunds", "settlements"):
                await app.navigate(resource)
                await app.workers.wait_for_complete()
            await app.navigate("explorer")
            await pilot.pause()
            assert app.query_one("#operation", Select).value == "payments.list"
            app.query_one("#param-count", Input).value = "1"
            app.execute_explorer()
            await app.workers.wait_for_complete()
            assert calls[-1].url.params["count"] == "1"
    asyncio.run(scenario())
