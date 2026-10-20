"""Conservative masking for all display and export boundaries."""
import re
from typing import Any

SENSITIVE = re.compile(
    r"secret|authorization|password|token|email|contact|phone|vpa|card|account|"
    r"address|notes|description|receipt|customer_details|acquirer_data|utr|name", re.I
)


def redact(value: Any, secrets: tuple[str, ...] = ()) -> Any:
    if isinstance(value, dict):
        return {redact(str(k), secrets): "[REDACTED]" if SENSITIVE.search(str(k)) else redact(v, secrets)
                for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, secrets) for v in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
    return value
