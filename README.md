# Personal Expense Manager

A command-line app to record, search, update and delete personal expenses.
Data is saved in `expenses.json` (created automatically on first run).

## Run
```
python main.py
```
Run the tests:
```
python -m unittest -v
```
Requires Python 3.8+. No third-party packages.

## Files
| File | Purpose |
|------|---------|
| `main.py` | `ExpenseApp`: menu, prompts and printing. The only file that uses `input()`/`print()` for the UI. |
| `expense.py` | `Expense`: one record. Validates itself; converts to/from dicts. |
| `expense_manager.py` | `ExpenseManager`: add/update/delete, filters, totals, monthly summary, budget. |
| `json_storage.py` | `JsonStorage`: the only file that reads/writes the disk. |
| `validators.py` | Regex + calendar + Decimal validation helpers. |
| `test_expense_manager.py` | Unit tests (valid, invalid, persistence, corrupted files). |

## How the pieces fit
`ExpenseApp` -> `ExpenseManager` -> `JsonStorage`, with `Expense` objects flowing through.
Each layer only talks to the one below it (composition).

## Key design decisions
- **Money uses `Decimal`**, stored in JSON as strings like `"12.50"`.
- **Dates**: regex checks the `YYYY-MM-DD` shape, `datetime.strptime` checks the date is real (so `2026-02-30` is rejected).
- **Safe saving**: write to a temp file, then `os.replace`. Memory is updated only after the save succeeds.
- **Corrupted JSON** is never overwritten; the app explains the problem and exits.
- **IDs are never reused**, even after deletions (`next_id` is stored in the file).
- Every record is validated when loaded; duplicate IDs are rejected.

## Data file format
```json
{
  "monthly_budget": "500.00",
  "next_id": 3,
  "expenses": [
    {"id": 1, "title": "Coffee", "amount": "3.50", "category": "Food",
     "date": "2026-10-14", "notes": ""}
  ]
}
```

## Manual test checklist
- Add with bad amount (`abc`, `-5`, `0`) and bad date (`2026-02-30`): re-prompted.
- Add, exit, restart: expense still there.
- Break `expenses.json` (delete a brace): app refuses to start and leaves the file untouched.
- Delete asks for confirmation; answering anything other than `y` cancels.
- Set budget, add expenses over it: warning appears in "Budget remaining".

## Ideas for next version
Edit categories list, CSV export, sort options, a database, a GUI.
