"""main.py - the command-line menu (ExpenseApp). Only this file prints and reads input."""

import sys
from datetime import date as date_type

import validators
from expense_manager import ExpenseManager, ExpenseNotFoundError
from json_storage import JsonStorage, StorageError

HEADER = f"{'ID':<5}{'Date':<12}{'Category':<16}{'Amount':>10}  Title"


def ask(prompt, parser, allow_blank=False):
    """Keep asking until parser accepts the input. Blank returns None if allowed."""
    while True:
        raw = input(prompt).strip()
        if allow_blank and raw == "":
            return None
        try:
            return parser(raw)
        except ValueError as err:
            print(f"  Invalid input: {err}")


def print_expenses(expenses):
    if not expenses:
        print("No expenses found.")
        return
    print(HEADER)
    print("-" * 60)
    for expense in expenses:
        print(expense)
    print("-" * 60)
    print(f"{len(expenses)} expense(s), total {ExpenseManager.total(expenses):.2f}")


def print_detail(expense):
    print(f"ID:       {expense.id}")
    print(f"Title:    {expense.title}")
    print(f"Amount:   {expense.amount:.2f}")
    print(f"Category: {expense.category}")
    print(f"Date:     {expense.date}")
    print(f"Notes:    {expense.notes or '-'}")


class ExpenseApp:
    def __init__(self, manager):
        self.manager = manager
        self.actions = {
            "1": ("Add expense", self.add),
            "2": ("View all expenses", self.view_all),
            "3": ("Search by ID", self.search_by_id),
            "4": ("Filter by category", self.filter_category),
            "5": ("Filter by date / date range", self.filter_dates),
            "6": ("Update expense", self.update),
            "7": ("Delete expense", self.delete),
            "8": ("Total expenses", self.total),
            "9": ("Totals by category", self.by_category),
            "10": ("Monthly summary", self.monthly),
            "11": ("Set monthly budget", self.set_budget),
            "12": ("Budget remaining", self.budget_remaining),
            "0": ("Exit", None),
        }

    def run(self):
        while True:
            self.show_menu()
            choice = input("Choose an option: ").strip()
            if choice == "0":
                print("Goodbye! Your expenses are saved.")
                return
            action = self.actions.get(choice)
            if action is None:
                print("Please choose a number from the menu.")
                continue
            try:
                action[1]()
            except (ValueError, ExpenseNotFoundError, StorageError) as err:
                print(f"Error: {err}")

    def show_menu(self):
        print("\n=== Personal Expense Manager ===")
        for key, (label, _) in self.actions.items():
            print(f"{key:>3}. {label}")

    # ---------- actions ----------
    def add(self):
        title = ask("Title: ", validators.parse_title)
        amount = ask("Amount: ", validators.parse_amount)
        category = ask("Category (Food, Travel, Education, Shopping, Other...): ", validators.parse_category)
        today = date_type.today().isoformat()
        date = ask(f"Date YYYY-MM-DD (Enter for {today}): ", validators.parse_date, allow_blank=True) or today
        notes = ask("Notes (optional): ", validators.parse_notes)
        expense = self.manager.add_expense(title, amount, category, date, notes)
        print(f"Added expense with ID {expense.id}.")

    def view_all(self):
        print_expenses(self.manager.get_all())

    def search_by_id(self):
        expense_id = ask("Expense ID: ", validators.parse_id)
        print_detail(self.manager.get_by_id(expense_id))

    def filter_category(self):
        category = ask("Category: ", validators.parse_category)
        print_expenses(self.manager.filter_by_category(category))

    def filter_dates(self):
        start = ask("Start date YYYY-MM-DD: ", validators.parse_date)
        end = ask("End date YYYY-MM-DD (Enter for same day): ", validators.parse_date, allow_blank=True)
        print_expenses(self.manager.filter_by_date_range(start, end))

    def update(self):
        expense_id = ask("ID of expense to update: ", validators.parse_id)
        current = self.manager.get_by_id(expense_id)
        print_detail(current)
        print("Press Enter to keep a value. For notes, type - to clear them.")
        title = ask("New title: ", validators.parse_title, allow_blank=True)
        amount = ask("New amount: ", validators.parse_amount, allow_blank=True)
        category = ask("New category: ", validators.parse_category, allow_blank=True)
        date = ask("New date: ", validators.parse_date, allow_blank=True)
        notes = ask("New notes: ", lambda t: "" if t == "-" else validators.parse_notes(t), allow_blank=True)
        updated = self.manager.update_expense(expense_id, title, amount, category, date, notes)
        print("Updated:")
        print_detail(updated)

    def delete(self):
        expense_id = ask("ID of expense to delete: ", validators.parse_id)
        print_detail(self.manager.get_by_id(expense_id))
        if input("Delete this expense? (y/N): ").strip().lower() == "y":
            self.manager.delete_expense(expense_id)
            print("Deleted.")
        else:
            print("Cancelled. Nothing was deleted.")

    def total(self):
        print(f"Total expenses: {self.manager.total_all():.2f}")

    def by_category(self):
        totals = self.manager.totals_by_category()
        if not totals:
            print("No expenses yet.")
            return
        for category, amount in totals.items():
            print(f"{category:<16}{amount:>10.2f}")

    def monthly(self):
        month = ask("Month YYYY-MM: ", validators.parse_month)
        summary = self.manager.monthly_summary(month)
        print(f"\nSummary for {summary['month']}: {summary['count']} expense(s), total {summary['total']:.2f}")
        for category, amount in summary["by_category"].items():
            print(f"  {category:<16}{amount:>10.2f}")

    def set_budget(self):
        amount = ask("Monthly budget: ", validators.parse_amount)
        print(f"Monthly budget set to {self.manager.set_budget(amount):.2f}.")

    def budget_remaining(self):
        default_month = date_type.today().strftime("%Y-%m")
        month = ask(f"Month YYYY-MM (Enter for {default_month}): ", validators.parse_month, allow_blank=True) or default_month
        status = self.manager.budget_status(month)
        print(f"Budget:    {status['budget']:.2f}")
        print(f"Spent:     {status['spent']:.2f}")
        print(f"Remaining: {status['remaining']:.2f}")
        if status["remaining"] < 0:
            print("Warning: you are over budget this month!")


def main():
    try:
        manager = ExpenseManager(JsonStorage("expenses.json"))
    except StorageError as err:
        print(f"Cannot start: {err}")
        sys.exit(1)
    try:
        ExpenseApp(manager).run()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting. Saved data is safe.")


if __name__ == "__main__":
    main()
