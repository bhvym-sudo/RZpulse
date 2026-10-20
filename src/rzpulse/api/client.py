"""Direct, bounded, read-only HTTP transport. Original JSON remains in memory."""
import asyncio
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from rzpulse.api.errors import (
    APIError, AuthenticationError, NotFound, PermissionDenied, ProtocolError,
    RateLimited, ServerError, TransportError,
)
from rzpulse.api.registry import REGISTRY
from rzpulse.config import Settings


class RazorpayClient:
    def __init__(self, settings: Settings, *, transport=None, sleep=asyncio.sleep):
        self.http = httpx.AsyncClient(
            base_url="https://api.razorpay.com", trust_env=False,
            auth=httpx.BasicAuth(settings.key_id.get_secret_value(),
                                settings.key_secret.get_secret_value()),
            timeout=httpx.Timeout(20, connect=5), follow_redirects=False, transport=transport,
            headers={"User-Agent": "RZPulse/0.1.0"},
        )
        self.sleep = sleep
        self.last_status: int | None = None

    async def close(self):
        await self.http.aclose()

    @staticmethod
    def retry_delay(header: str | None, attempt: int) -> float:
        if header:
            try:
                return max(0, float(header))
            except ValueError:
                try:
                    return max(0, (parsedate_to_datetime(header) -
                                   datetime.now(timezone.utc)).total_seconds())
                except (ValueError, TypeError, OverflowError):
                    pass
        return 2 ** attempt + random.random()

    async def execute(self, operation: str, parameters: dict | None = None) -> dict:
        op = REGISTRY.get(operation)
        if op is None or not op.read_only or op.method != "GET":
            raise ValueError("Only registered read-only operations are enabled.")
        path, params = op.prepare(parameters or {})
        self.last_status = None
        for attempt in range(3):
            try:
                response = await self.http.request(op.method, path, params=params)
            except httpx.TransportError:
                if attempt < 2:
                    await self.sleep(self.retry_delay(None, attempt))
                    continue
                raise TransportError("Connection failed. Check network access and retry.") from None
            self.last_status = response.status_code
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                delay = self.retry_delay(response.headers.get("Retry-After"), attempt)
                # A long server cooldown is surfaced; never retry earlier than requested.
                if delay <= 60:
                    await self.sleep(delay)
                    continue
            status = response.status_code
            if status >= 300:
                cls, message = {
                    401: (AuthenticationError, "Authentication failed. Check credentials and mode."),
                    403: (PermissionDenied, "Access denied. Account may lack product access or permission."),
                    404: (NotFound, "Resource not found in the selected account and mode."),
                    429: (RateLimited, "Rate limited. Wait before refreshing."),
                }.get(status, (ServerError, "Razorpay service error. Try again later.") if status >= 500
                      else (APIError, "Request rejected. Check parameters and account permissions."))
                # Never reflect upstream strings: errors can echo credentials or customer data.
                raise cls(message, status)
            try:
                data = response.json()
            except ValueError:
                raise ProtocolError("Razorpay returned invalid JSON.", status) from None
            if not isinstance(data, dict):
                raise ProtocolError("Unexpected API response shape.", status)
            if op.name == "list" and (not isinstance(data.get("items"), list) or
                                      not all(isinstance(x, dict) for x in data["items"])):
                raise ProtocolError("Expected a collection of records.", status)
            return data
        raise AssertionError("unreachable")
