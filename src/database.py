"""Small, explicit SQLite helpers shared by the assignment scripts."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def connect(database_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite database with foreign-key checks enabled."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Cursor]:
    """Commit only if all statements succeed; otherwise roll back."""
    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def create_books_table(connection: sqlite3.Connection) -> None:
    """Create the schema used by the book API pipeline."""
    with transaction(connection) as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY,
                source_key TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                publication_year INTEGER,
                retrieved_at TEXT NOT NULL,
                CHECK (publication_year IS NULL OR publication_year BETWEEN 0 AND 2100)
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)")


def create_users_table(connection: sqlite3.Connection) -> None:
    """Create the schema used by the CSV import pipeline."""
    with transaction(connection) as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                imported_at TEXT NOT NULL
            )
            """
        )