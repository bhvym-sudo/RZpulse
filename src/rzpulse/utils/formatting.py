from datetime import datetime, timezone
from decimal import Decimal

# Unknown currencies are deliberately shown as subunits rather than guessed.
EXPONENTS = {c: 2 for c in "INR USD EUR GBP AUD CAD SGD MYR AED CHF CNY HKD".split()}
EXPONENTS.update(JPY=0, KRW=0, BHD=3, KWD=3, OMR=3)


def money(amount: int | None, currency: str | None) -> str:
    if amount is None:
        return "—"
    if currency not in EXPONENTS:
        return f"{currency or 'unknown currency'} {amount:,} subunits"
    digits = EXPONENTS[currency]
    return f"{currency} {Decimal(amount) / Decimal(10 ** digits):,.{digits}f}"


def timestamp(value: int | None) -> str:
    if value is None:
        return "—"
    try:
        return datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, OverflowError, OSError, TypeError):
        return "—"
