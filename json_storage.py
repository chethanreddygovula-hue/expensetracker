"""json_storage.py - the ONLY file that touches the disk."""

import json
import os
from pathlib import Path


class StorageError(Exception):
    """Raised when the data file cannot be read or written safely."""


class JsonStorage:
    def __init__(self, path="expenses.json"):
        self.path = Path(path)

    def load(self):
        """Return the stored data as a dict. Creates the file if missing."""
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            data = {"monthly_budget": None, "next_id": 1, "expenses": []}
            self.save(data)
            return data
        except (json.JSONDecodeError, UnicodeDecodeError) as err:
            # Do NOT overwrite: the user may be able to repair the file.
            raise StorageError(
                f"{self.path} is corrupted ({err}). It has not been changed. "
                "Fix it or rename it, then restart."
            ) from err
        except OSError as err:
            raise StorageError(f"Could not read {self.path}: {err}") from err

        if not isinstance(data, dict) or not isinstance(data.get("expenses"), list):
            raise StorageError(f"{self.path} does not have the expected structure. It has not been changed.")
        return data

    def save(self, data):
        """Write data safely: temp file first, then swap it in."""
        temp_path = self.path.with_name(self.path.name + ".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2)
            os.replace(temp_path, self.path)
        except OSError as err:
            raise StorageError(f"Could not save to {self.path}: {err}") from err
