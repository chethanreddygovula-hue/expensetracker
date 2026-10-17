"""validators.py - input checking helpers.

Every function takes a raw string, returns a clean value,
or raises ValueError with a friendly message.
Regex checks the *shape* of the text; other code checks the *meaning*.
"""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

# re.compile builds the pattern once; fullmatch() demands the WHOLE string matches.
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
MONTH_PATTERN = re.compile(r"\d{4}-\d{2}")
AMOUNT_PATTERN = re.compile(r"\d{1,9}(\.\d{1,2})?")
CATEGORY_PATTERN = re.compile(r"[A-Za-z][A-Za-z &'-]{0,29}")

MAX_TITLE = 60
MAX_NOTES = 200
CENT = Decimal("0.01")


def parse_date(text):
    """Return a valid 'YYYY-MM-DD' string."""
    text = str(text).strip()
    if not DATE_PATTERN.fullmatch(text):
        raise ValueError("Date must look like YYYY-MM-DD (e.g. 2026-10-14).")
    try:
        # Regex can't know 2026-02-30 is impossible; strptime can.
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"'{text}' is not a real calendar date.") from None
    return text


def parse_month(text):
    """Return a valid 'YYYY-MM' string."""
    text = str(text).strip()
    if not MONTH_PATTERN.fullmatch(text):
        raise ValueError("Month must look like YYYY-MM (e.g. 2026-10).")
    try:
        datetime.strptime(text, "%Y-%m")
    except ValueError:
        raise ValueError(f"'{text}' is not a real month.") from None
    return text


def parse_amount(text):
    """Return a positive Decimal rounded to 2 places."""
    text = str(text).strip()
    # Regex only screens the shape; Decimal does the real conversion.
    if not AMOUNT_PATTERN.fullmatch(text):
        raise ValueError("Amount must be a number like 12 or 12.50 (no symbols or commas).")
    try:
        amount = Decimal(text).quantize(CENT)
    except InvalidOperation:
        raise ValueError(f"'{text}' is not a valid amount.") from None
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    return amount


def parse_title(text):
    text = str(text).strip()
    if not text:
        raise ValueError("Title cannot be empty.")
    if len(text) > MAX_TITLE:
        raise ValueError(f"Title must be at most {MAX_TITLE} characters.")
    return text


def parse_category(text):
    text = str(text).strip()
    if not CATEGORY_PATTERN.fullmatch(text):
        raise ValueError("Category must start with a letter and use only letters, spaces, &, ' or - (max 30).")
    return text.title()


def parse_notes(text):
    text = str(text).strip()
    if len(text) > MAX_NOTES:
        raise ValueError(f"Notes must be at most {MAX_NOTES} characters.")
    return text


def parse_id(text):
    """Return a positive int."""
    try:
        value = int(str(text).strip())
    except ValueError:
        raise ValueError("ID must be a whole number.") from None
    if value < 1:
        raise ValueError("ID must be 1 or greater.")
    return value
