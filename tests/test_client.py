import asyncio
import base64
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest

from rzpulse.api.client import RazorpayClient
from rzpulse.api.errors import (
    APIError, AuthenticationError, NotFound, PermissionDenied, ProtocolError,
    RateLimited, ServerError, TransportError,
)
from rzpulse.api.registry import REGISTRY


def run(coro):
    return asyncio.run(coro)


def test_auth_url_params_and_pagination(settings):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"items": [{"id": "pay_1"}], "count": 1})
    async def scenario():
        client = RazorpayClient(settings, transport=httpx.MockTransport(handler))
        try:
            for skip in [0, 25]:
                await client.execute("payments.list", {"count": 25, "skip": skip, "from": 1700000000})
            await client.execute("orders.fetch", {"id": "order_abc"})
        finally:
            await client.close()
    run(scenario())
    assert str(requests[0].url).startswith("https://api.razorpay.com/v1/payments?")
    assert requests[1].url.params["skip"] == "25"
    assert requests[0].url.params["from"] == "1700000000"
    auth = base64.b64encode(b"rzp_test_unit:unit-secret").decode()
    assert requests[0].headers["Authorization"] == f"Basic {auth}"
    assert requests[2].url.path == "/v1/orders/order_abc"


@pytest.mark.parametrize("status,exception,retries", [
    (400, APIError, 1), (401, AuthenticationError, 1), (403, PermissionDenied, 1),
    (404, NotFound, 1), (429, RateLimited, 3), (500, ServerError, 3), (302, APIError, 1),
])
def test_errors_and_retry_safety(settings, status, exception, retries):
    calls, delays = [], []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": {"description": "unit-secret"}},
                              headers={"Retry-After": "0", "Location": "https://example.com"})
    async def sleep(delay):
        delays.append(delay)
    async def scenario():
        client = RazorpayClient(settings, transport=httpx.MockTransport(handler), sleep=sleep)
        try:
            with pytest.raises(exception) as error:
                await client.execute("refunds.list")
            assert "unit-secret" not in str(error.value)
            assert error.value.status == status
            with pytest.raises(ValueError):
                await client.execute("refunds.create", {"amount": 100})
        finally:
            await client.close()
    run(scenario())
    assert len(calls) == retries
    assert all(r.method == "GET" for r in calls)


def test_retry_after_then_success(settings):
    delays = []
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "3"}) if len(calls) == 1 else \
            httpx.Response(200, json={"items": [], "count": 0})
    async def sleep(delay):
        delays.append(delay)
    async def scenario():
        client = RazorpayClient(settings, transport=httpx.MockTransport(handler), sleep=sleep)
        try:
            assert (await client.execute("payments.list"))["items"] == []
        finally:
            await client.close()
    run(scenario())
    assert delays == [3]
    date = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=20))
    assert 18 <= RazorpayClient.retry_delay(date, 0) <= 20


def test_long_retry_after_does_not_retry_early(settings):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "120"})
    async def scenario():
        client = RazorpayClient(settings, transport=httpx.MockTransport(handler))
        try:
            with pytest.raises(RateLimited):
                await client.execute("payments.list")
        finally:
            await client.close()
    run(scenario())
    assert len(calls) == 1


@pytest.mark.parametrize("data", [[], {"items": "bad"}, {"items": [1]}])
def test_invalid_collection(settings, data):
    async def scenario():
        client = RazorpayClient(settings, transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json=data)))
        try:
            with pytest.raises(ProtocolError):
                await client.execute("payments.list")
        finally:
            await client.close()
    run(scenario())


def test_transport_error_redacted(settings):
    delays = []
    def handler(request):
        raise httpx.ConnectError("unit-secret", request=request)
    async def sleep(delay):
        delays.append(delay)
    async def scenario():
        client = RazorpayClient(settings, transport=httpx.MockTransport(handler), sleep=sleep)
        try:
            with pytest.raises(TransportError) as error:
                await client.execute("payments.list")
            assert "unit-secret" not in str(error.value)
        finally:
            await client.close()
    run(scenario())
    assert len(delays) == 2


def test_registry_validation():
    assert len(REGISTRY) == 8
    for key, op in REGISTRY.items():
        assert op.read_only and op.method == "GET"
        assert op.documentation.startswith("https://razorpay.com/docs/api/")
        assert op.path.startswith("/v1/")
        if op.name == "fetch":
            for bad in ("https://example.com", "../payments", "pay_a?secret=1", "pay_a/b"):
                with pytest.raises(ValueError):
                    op.prepare({"id": bad})
        else:
            for params in ({"count": 101}, {"skip": -1}, {"count": 0}, {"status": "paid"},
                           {"from": 1700000001, "to": 1700000000}, {"count": "SECRET"}):
                with pytest.raises(ValueError) as error:
                    op.prepare(params)
                assert "SECRET" not in str(error.value)
    assert REGISTRY["orders.list"].prepare({"authorized": 1})[1]["authorized"] == 1


def test_registry_refuses_absolute_endpoint():
    from rzpulse.api.registry import Operation
    with pytest.raises(ValueError):
        Operation("payments", "list", "GET", "https://example.com/payments", "bad",
                  "https://razorpay.com/docs/api/")
    assert REGISTRY["orders.list"].prepare({"authorized": "1"})[1]["authorized"] == 1
