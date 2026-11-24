"""Validate and import a user CSV into SQLite using parameterized SQL."""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from src.database import connect, create_users_table, transaction

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@dataclass(frozen=True)
class User:
    name: str
    email: str


def validate_user(row: dict[str, str | None], row_number: int) -> User:
    """Normalize one CSV row and reject malformed data with a useful location."""
    name = " ".join((row.get("name") or "").split())
    email = (row.get("email") or "").strip().casefold()
    if not 1 <= len(name) <= 120:
        raise ValueError(f"Row {row_number}: name must contain 1-120 characters")
    if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
        raise ValueError(f"Row {row_number}: invalid email address")
    return User(name=name, email=email)


def read_users(csv_path: str | Path) -> list[User]:
    """Read a CSV with exactly the required headers and no silently bad rows."""
    with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["name", "email"]:
            raise ValueError("CSV must contain exactly these headers: name,email")
        return [validate_user(row, row_number) for row_number, row in enumerate(reader, start=2)]


def import_users(csv_path: str | Path, database_path: str | Path) -> int:
    """Import users atomically; a repeated email updates the display name."""
    users = read_users(csv_path)
    imported_at = datetime.now(UTC).isoformat()
    connection = connect(database_path)
    try:
        create_users_table(connection)
        with transaction(connection) as cursor:
            cursor.executemany(
                """
                INSERT INTO users (name, email, imported_at)
                VALUES (?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    name = excluded.name,
                    imported_at = excluded.imported_at
                """,
                [(user.name, user.email, imported_at) for user in users],
            )
        return len(users)
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=Path("data/users.csv"), help="Input CSV path")
    parser.add_argument("--db", type=Path, default=Path("data/users.db"), help="SQLite file path")
    args = parser.parse_args()

    count = import_users(args.csv, args.db)
    print(f"Imported or updated {count} user(s) in {args.db}.")


if __name__ == "__main__":
    main()