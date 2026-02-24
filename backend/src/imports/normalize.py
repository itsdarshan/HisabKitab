"""Normalize and validate the raw JSON string returned by the vision LLM."""

import json
import re
from datetime import datetime


def parse_llm_response(raw: str) -> list[dict]:
    """
    Accept the raw text from the LLM, strip markdown fences if present,
    parse JSON, and validate/clean each transaction dict.

    Handles truncated JSON gracefully by extracting individual
    complete JSON objects from the response even when the array
    was cut off mid-way (finish_reason: length).
    """
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    cleaned = cleaned.strip("`").strip()

    data = None

    # 1. Try parsing as valid JSON first
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 2. Try finding a complete JSON array in the text
    if data is None:
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                pass

    # 3. Try repairing truncated JSON by closing the array
    if data is None:
        match = re.search(r"\[.*", cleaned, re.DOTALL)
        if match:
            fragment = match.group().rstrip().rstrip(",")
            # Try closing with }] in case we're mid-object
            for suffix in ["]}", "}", "]", "}]"]:
                try:
                    data = json.loads(fragment + suffix)
                    break
                except json.JSONDecodeError:
                    continue

    # 4. Last resort: extract all individual {...} objects via regex
    if data is None:
        data = []
        for m in re.finditer(r"\{[^{}]*\}", cleaned):
            try:
                obj = json.loads(m.group())
                data.append(obj)
            except json.JSONDecodeError:
                continue

    if not data:
        return []

    if not isinstance(data, list):
        data = [data]

    results: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        txn = _clean_transaction(item)
        if txn:
            results.append(txn)
    return results


def _clean_transaction(raw: dict) -> dict | None:
    """Validate and normalise a single transaction dict."""
    # Amount is required
    amount = _parse_amount(raw.get("amount"))
    if amount is None:
        return None

    txn_type = str(raw.get("txn_type", "debit")).lower()
    if txn_type not in ("debit", "credit"):
        txn_type = "debit"

    date_str = _parse_date(raw.get("date"))
    if date_str is None:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")

    category = str(raw.get("category", "")).strip() or None

    return {
        "date": date_str,
        "description": str(raw.get("description", "")).strip() or None,
        "merchant": str(raw.get("merchant", "")).strip() or None,
        "amount": abs(amount),
        "txn_type": txn_type,
        "balance": _parse_amount(raw.get("balance")),
        "currency": str(raw.get("currency", "USD")).upper()[:3],
        "category": category,
    }


def _parse_amount(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        cleaned = re.sub(r"[^\d.\-]", "", str(val))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def _parse_date(val) -> str | None:
    if val is None:
        return None
    val = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %b %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(val, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None
