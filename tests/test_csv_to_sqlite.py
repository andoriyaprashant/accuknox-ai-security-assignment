import sqlite3

import pytest

from src.csv_to_sqlite import import_users, read_users


def test_import_users_normalizes_and_upserts(tmp_path) -> None:
    csv_file = tmp_path / "users.csv"
    database = tmp_path / "users.db"
    csv_file.write_text("name,email\n Ada Lovelace ,ADA@EXAMPLE.COM\n", encoding="utf-8")

    assert import_users(csv_file, database) == 1
    connection = sqlite3.connect(database)
    try:
        row = connection.execute("SELECT name, email FROM users").fetchone()
    finally:
        connection.close()

    assert row == ("Ada Lovelace", "ada@example.com")


def test_read_users_rejects_invalid_email(tmp_path) -> None:
    csv_file = tmp_path / "users.csv"
    csv_file.write_text("name,email\nAda,not-an-email\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid email"):
        read_users(csv_file)