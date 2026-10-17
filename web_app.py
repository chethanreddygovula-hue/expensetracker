"""web_app.py - a minimal browser frontend server (standard library only).

It reuses ExpenseManager unchanged: this file only translates
HTTP requests <-> manager method calls.

Run from the project folder:  python web_app.py
Then open http://127.0.0.1:8000
"""

import json
import sys
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import validators
from expense_manager import ExpenseManager, ExpenseNotFoundError
from json_storage import JsonStorage, StorageError

INDEX_FILE = Path(__file__).parent / "index.html"
HOST, PORT = "127.0.0.1", 8000  # localhost only: not reachable from other computers


def money(value):
    return f"{value:.2f}"


def make_handler(manager):
    """Build a handler class that knows about one ExpenseManager (avoids a global)."""

    class Handler(BaseHTTPRequestHandler):
        # ---------- sending ----------
        def _send(self, status, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_page(self):
            body = INDEX_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        # ---------- reading ----------
        def _read_json(self):
            # Requiring this content type blocks simple cross-site form posts.
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                raise ValueError("Request must be sent as JSON.")
            length = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(length) or b"{}")  # JSONDecodeError is a ValueError
            if not isinstance(data, dict):
                raise ValueError("Request body must be a JSON object.")
            return data

        # ---------- routing ----------
        def _handle(self, method):
            url = urlparse(self.path)
            query = {key: values[0] for key, values in parse_qs(url.query).items()}
            try:
                if method == "GET" and url.path == "/":
                    self._send_page()
                    return
                body = self._read_json() if method in ("POST", "PUT") else {}
                status, payload = self._dispatch(method, url.path, query, body)
                self._send(status, payload)
            except ExpenseNotFoundError as err:
                self._send(404, {"error": str(err)})
            except ValueError as err:
                self._send(400, {"error": str(err)})
            except StorageError as err:
                self._send(500, {"error": str(err)})

        def _dispatch(self, method, path, query, body):
            parts = path.strip("/").split("/")

            if parts == ["api", "expenses"]:
                if method == "GET":
                    return 200, [e.to_dict() for e in self._list(query)]
                if method == "POST":
                    expense = manager.add_expense(
                        body.get("title", ""), body.get("amount", ""),
                        body.get("category", ""), body.get("date", ""), body.get("notes", ""),
                    )
                    return 201, expense.to_dict()

            if len(parts) == 3 and parts[:2] == ["api", "expenses"]:
                expense_id = validators.parse_id(parts[2])
                if method == "PUT":
                    expense = manager.update_expense(
                        expense_id, body.get("title"), body.get("amount"),
                        body.get("category"), body.get("date"), body.get("notes"),
                    )
                    return 200, expense.to_dict()
                if method == "DELETE":
                    manager.delete_expense(expense_id)
                    return 200, {"deleted": expense_id}

            if path == "/api/summary" and method == "GET":
                return 200, self._summary(query.get("month") or date.today().strftime("%Y-%m"))

            if path == "/api/budget" and method == "POST":
                return 200, {"budget": money(manager.set_budget(body.get("amount", "")))}

            return 404, {"error": "Not found."}

        # ---------- helpers ----------
        def _list(self, query):
            expenses = manager.get_all()
            if query.get("start"):
                expenses = manager.filter_by_date_range(query["start"], query.get("end"))
            if query.get("category"):
                wanted = query["category"].strip().casefold()
                expenses = [e for e in expenses if e.category.casefold() == wanted]
            return expenses

        def _summary(self, month):
            summary = manager.monthly_summary(month)
            result = {
                "month": summary["month"],
                "spent": money(summary["total"]),
                "by_category": {c: money(a) for c, a in summary["by_category"].items()},
                "budget": None,
                "remaining": None,
            }
            if manager.budget is not None:
                status = manager.budget_status(month)
                result["budget"] = money(status["budget"])
                result["remaining"] = money(status["remaining"])
            return result

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

        def do_PUT(self):
            self._handle("PUT")

        def do_DELETE(self):
            self._handle("DELETE")

    return Handler


def main():
    try:
        manager = ExpenseManager(JsonStorage("expenses.json"))
    except StorageError as err:
        print(f"Cannot start: {err}")
        sys.exit(1)

    server = HTTPServer((HOST, PORT), make_handler(manager))
    print(f"Open http://{HOST}:{PORT}  (press Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Saved data is safe.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
