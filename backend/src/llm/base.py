"""Abstract base for vision-LLM adapters."""

from abc import ABC, abstractmethod


EXTRACTION_PROMPT = """You are a financial document parser. Analyse this bank statement image carefully.

Extract EVERY transaction visible on the page as a JSON array. Each element must have these keys:
- "date": transaction date in ISO-8601 format (YYYY-MM-DD). Infer the year from context if only day/month shown.
- "description": the full transaction description / narration as shown.
- "merchant": the merchant or payee name (best guess from description). Use null if unclear.
- "amount": the absolute numeric amount (no currency symbols). Always positive.
- "txn_type": "debit" if money was spent/withdrawn, "credit" if money was received/deposited.
- "balance": the running balance shown after this transaction. Use null if not shown.
- "currency": three-letter currency code (e.g. "USD", "INR", "GBP"). Infer from the document.
- "category": assign one of the following categories to each transaction based on the description/merchant. If the document itself shows a category, use that. Otherwise, deduce the most appropriate one:
  Groceries, Dining, Transport, Shopping, Bills & Utilities, Entertainment, Health, Travel, Education, Income, Transfer, Other

Rules:
1. Return ONLY a valid JSON array — no markdown fences, no explanation.
2. If no transactions are found on this page, return an empty array [].
3. Do NOT invent transactions — only extract what is visible.
4. For "category", always pick the single best match from the list above. Use "Other" if none fits.

Respond with the JSON array now."""


class VisionAdapter(ABC):
    @abstractmethod
    def extract_transactions(self, image_path: str) -> str:
        """Send image to the vision model and return the raw text response."""
        ...
