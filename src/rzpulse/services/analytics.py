from collections import defaultdict


def summarize(items: list[dict]) -> dict:
    totals = defaultdict(int)
    for item in items:
        if item.get("status") == "captured":
            totals[item.get("currency") or "unknown"] += item.get("amount") or 0
    return {"payments": len(items),
            "successful": sum(x.get("status") == "captured" for x in items),
            "failed": sum(x.get("status") == "failed" for x in items),
            "captured": dict(totals)}


def refund_summary(items: list[dict]) -> dict:
    totals = defaultdict(int)
    processed = [item for item in items if item.get("status") == "processed"]
    for item in processed:
        totals[item.get("currency") or "unknown"] += item.get("amount") or 0
    return {"count": len(items), "processed": len(processed), "amounts": dict(totals)}
