"""expense_manager.py - business logic. Never prints, never touches files directly."""

from decimal import Decimal

import validators
from expense import Expense
from json_storage import StorageError


class ExpenseNotFoundError(Exception):
    """Raised when an expense ID does not exist."""


class ExpenseManager:
    def __init__(self, storage):
        self._storage = storage  # composition: the manager HAS a storage
        data = storage.load()
        self._expenses = self._build_expenses(data["expenses"])
        self._budget = self._load_budget(data.get("monthly_budget"))
        highest = max((e.id for e in self._expenses), default=0)
        stored_next = data.get("next_id", 1)
        if isinstance(stored_next, bool) or not isinstance(stored_next, int):
            stored_next = 1
        self._next_id = max(stored_next, highest + 1)

    # ---------- loading helpers ----------
    @staticmethod
    def _build_expenses(records):
        expenses, seen = [], set()
        for index, record in enumerate(records, start=1):
            try:
                expense = Expense.from_dict(record)
            except ValueError as err:
                raise StorageError(f"Record #{index} in the data file is invalid: {err}") from err
            if expense.id in seen:
                raise StorageError(f"Duplicate expense ID {expense.id} in the data file.")
            seen.add(expense.id)
            expenses.append(expense)
        return expenses

    @staticmethod
    def _load_budget(value):
        if value is None:
            return None
        try:
            return validators.parse_amount(value)
        except ValueError as err:
            raise StorageError(f"Stored monthly budget is invalid: {err}") from err

    # ---------- saving ----------
    def _commit(self, expenses, budget, next_id):
        """Save first; only update memory if saving worked."""
        data = {
            "monthly_budget": None if budget is None else f"{budget:.2f}",
            "next_id": next_id,
            "expenses": [e.to_dict() for e in expenses],
        }
        self._storage.save(data)
        self._expenses, self._budget, self._next_id = expenses, budget, next_id

    # ---------- create / read ----------
    def add_expense(self, title, amount, category, date, notes=""):
        expense = Expense(self._next_id, title, amount, category, date, notes)
        self._commit(self._expenses + [expense], self._budget, self._next_id + 1)
        return expense

    def get_all(self):
        return sorted(self._expenses, key=lambda e: (e.date, e.id))

    def get_by_id(self, expense_id):
        for expense in self._expenses:
            if expense.id == expense_id:
                return expense
        raise ExpenseNotFoundError(f"No expense with ID {expense_id}.")

    def filter_by_category(self, category):
        wanted = category.strip().casefold()
        return [e for e in self.get_all() if e.category.casefold() == wanted]

    def filter_by_date_range(self, start, end=None):
        start = validators.parse_date(start)
        end = validators.parse_date(end) if end else start
        if start > end:
            raise ValueError("Start date must not be after end date.")
        # ISO dates compare correctly as plain strings.
        return [e for e in self.get_all() if start <= e.date <= end]

    # ---------- update / delete ----------
    def update_expense(self, expense_id, title=None, amount=None, category=None, date=None, notes=None):
        old = self.get_by_id(expense_id)
        new = Expense(
            old.id,
            old.title if title is None else title,
            old.amount if amount is None else amount,
            old.category if category is None else category,
            old.date if date is None else date,
            old.notes if notes is None else notes,
        )
        updated = [new if e.id == expense_id else e for e in self._expenses]
        self._commit(updated, self._budget, self._next_id)
        return new

    def delete_expense(self, expense_id):
        removed = self.get_by_id(expense_id)
        remaining = [e for e in self._expenses if e.id != expense_id]
        self._commit(remaining, self._budget, self._next_id)
        return removed

    # ---------- calculations ----------
    @staticmethod
    def total(expenses):
        return sum((e.amount for e in expenses), Decimal("0.00"))

    def total_all(self):
        return self.total(self._expenses)

    def totals_by_category(self):
        totals = {}
        for e in self._expenses:
            totals[e.category] = totals.get(e.category, Decimal("0.00")) + e.amount
        return dict(sorted(totals.items()))

    def monthly_summary(self, month):
        month = validators.parse_month(month)
        items = [e for e in self._expenses if e.date.startswith(month)]
        by_category = {}
        for e in items:
            by_category[e.category] = by_category.get(e.category, Decimal("0.00")) + e.amount
        return {
            "month": month,
            "count": len(items),
            "total": self.total(items),
            "by_category": dict(sorted(by_category.items())),
        }

    # ---------- budget ----------
    @property
    def budget(self):
        return self._budget

    def set_budget(self, amount):
        value = validators.parse_amount(amount)
        self._commit(self._expenses, value, self._next_id)
        return value

    def budget_status(self, month):
        if self._budget is None:
            raise ValueError("No monthly budget set yet. Use the 'Set monthly budget' option first.")
        spent = self.monthly_summary(month)["total"]
        return {"budget": self._budget, "spent": spent, "remaining": self._budget - spent}
