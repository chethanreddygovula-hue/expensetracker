"""Run with:  python -m unittest -v"""

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import validators
from expense_manager import ExpenseManager, ExpenseNotFoundError
from json_storage import JsonStorage, StorageError


class TestValidators(unittest.TestCase):
    def test_good_date(self):
        self.assertEqual(validators.parse_date("2026-10-14"), "2026-10-14")

    def test_bad_date_format(self):
        for bad in ["14-10-2026", "2026/10/14", "abc", ""]:
            with self.assertRaises(ValueError):
                validators.parse_date(bad)

    def test_impossible_date(self):
        for bad in ["2026-02-30", "2026-13-01", "2026-00-10"]:
            with self.assertRaises(ValueError):
                validators.parse_date(bad)

    def test_amount(self):
        self.assertEqual(validators.parse_amount("12.5"), Decimal("12.50"))
        for bad in ["0", "-5", "abc", "1,000", "$5", "1.234", ""]:
            with self.assertRaises(ValueError):
                validators.parse_amount(bad)

    def test_category(self):
        self.assertEqual(validators.parse_category("  food "), "Food")
        with self.assertRaises(ValueError):
            validators.parse_category("123")


class TestManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "expenses.json"
        self.manager = ExpenseManager(JsonStorage(self.path))

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, title="Lunch", amount="10.00", category="Food", date="2026-10-01"):
        return self.manager.add_expense(title, amount, category, date)

    def test_file_created(self):
        self.assertTrue(self.path.exists())

    def test_persistence(self):
        self.add()
        reloaded = ExpenseManager(JsonStorage(self.path))
        self.assertEqual(len(reloaded.get_all()), 1)
        self.assertEqual(reloaded.get_all()[0].amount, Decimal("10.00"))

    def test_amount_stored_as_string(self):
        self.add(amount="7.5")
        raw = json.loads(self.path.read_text())
        self.assertEqual(raw["expenses"][0]["amount"], "7.50")

    def test_invalid_add_changes_nothing(self):
        with self.assertRaises(ValueError):
            self.add(amount="-1")
        self.assertEqual(self.manager.get_all(), [])

    def test_decimal_math(self):
        self.add(amount="0.10")
        self.add(amount="0.20")
        self.assertEqual(self.manager.total_all(), Decimal("0.30"))

    def test_update_and_delete(self):
        e = self.add()
        self.manager.update_expense(e.id, title="Dinner", amount="25")
        self.assertEqual(self.manager.get_by_id(e.id).title, "Dinner")
        self.manager.delete_expense(e.id)
        with self.assertRaises(ExpenseNotFoundError):
            self.manager.get_by_id(e.id)

    def test_ids_never_reused(self):
        first = self.add()
        self.manager.delete_expense(first.id)
        second = self.add()
        self.assertNotEqual(first.id, second.id)
        reloaded = ExpenseManager(JsonStorage(self.path))
        self.assertGreater(reloaded.add_expense("X", "1", "Other", "2026-10-02").id, second.id)

    def test_unknown_id(self):
        with self.assertRaises(ExpenseNotFoundError):
            self.manager.delete_expense(99)

    def test_filters(self):
        self.add(category="Food", date="2026-10-01")
        self.add(category="Travel", date="2026-10-15")
        self.assertEqual(len(self.manager.filter_by_category("food")), 1)
        self.assertEqual(len(self.manager.filter_by_date_range("2026-10-01", "2026-10-31")), 2)
        self.assertEqual(len(self.manager.filter_by_date_range("2026-10-15")), 1)
        with self.assertRaises(ValueError):
            self.manager.filter_by_date_range("2026-10-31", "2026-10-01")

    def test_summary_and_budget(self):
        self.add(amount="100", date="2026-10-01")
        self.add(amount="50", category="Travel", date="2026-11-01")
        summary = self.manager.monthly_summary("2026-10")
        self.assertEqual(summary["total"], Decimal("100.00"))
        with self.assertRaises(ValueError):
            self.manager.budget_status("2026-10")  # no budget yet
        self.manager.set_budget("300")
        self.assertEqual(self.manager.budget_status("2026-10")["remaining"], Decimal("200.00"))
        reloaded = ExpenseManager(JsonStorage(self.path))
        self.assertEqual(reloaded.budget, Decimal("300.00"))


class TestCorruptedFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "expenses.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_malformed_json_not_overwritten(self):
        self.path.write_text("{ this is not json")
        with self.assertRaises(StorageError):
            ExpenseManager(JsonStorage(self.path))
        self.assertEqual(self.path.read_text(), "{ this is not json")

    def test_invalid_record(self):
        bad = {"expenses": [{"id": 1, "title": "x", "amount": "-5.00", "category": "Food", "date": "2026-01-01"}]}
        self.path.write_text(json.dumps(bad))
        with self.assertRaises(StorageError):
            ExpenseManager(JsonStorage(self.path))

    def test_missing_field(self):
        self.path.write_text(json.dumps({"expenses": [{"id": 1}]}))
        with self.assertRaises(StorageError):
            ExpenseManager(JsonStorage(self.path))

    def test_duplicate_ids(self):
        rec = {"id": 1, "title": "x", "amount": "5.00", "category": "Food", "date": "2026-01-01", "notes": ""}
        self.path.write_text(json.dumps({"expenses": [rec, rec]}))
        with self.assertRaises(StorageError):
            ExpenseManager(JsonStorage(self.path))

    def test_wrong_structure(self):
        self.path.write_text("[]")
        with self.assertRaises(StorageError):
            ExpenseManager(JsonStorage(self.path))


if __name__ == "__main__":
    unittest.main()
