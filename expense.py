"""expense.py - the Expense class: one expense record."""

from decimal import Decimal

import validators


class Expense:
    """Holds the data of a single expense and validates it on creation."""

    def __init__(self, expense_id, title, amount, category, date, notes=""):
        if isinstance(expense_id, bool) or not isinstance(expense_id, int) or expense_id < 1:
            raise ValueError("Expense ID must be a positive whole number.")
        self.id = expense_id
        self.title = validators.parse_title(title)
        self.amount = validators.parse_amount(amount)  # Decimal
        self.category = validators.parse_category(category)
        self.date = validators.parse_date(date)
        self.notes = validators.parse_notes(notes)

    def to_dict(self):
        """Convert to a JSON-friendly dict (money stored as a 2-decimal string)."""
        return {
            "id": self.id,
            "title": self.title,
            "amount": f"{self.amount:.2f}",
            "category": self.category,
            "date": self.date,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an Expense from a dict loaded from JSON. Raises ValueError if bad."""
        if not isinstance(data, dict):
            raise ValueError("record is not an object")
        try:
            raw_amount = data["amount"]
            if not isinstance(raw_amount, str):
                raise ValueError("amount must be stored as a string")
            return cls(
                data["id"], data["title"], raw_amount,
                data["category"], data["date"], data.get("notes", ""),
            )
        except KeyError as err:
            raise ValueError(f"missing field {err}") from None

    def __str__(self):
        return f"{self.id:<5}{self.date:<12}{self.category:<16}{self.amount:>10.2f}  {self.title}"
