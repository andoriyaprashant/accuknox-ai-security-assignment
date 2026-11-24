"""Fetch book metadata from Open Library, validate it and store it in SQLite."""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import requests

from src.database import connect, create_books_table, transaction

SEARCH_URL = "https://openlibrary.org/search.json"
USER_AGENT = "accuknox-assignment/1.0 (take-home)"


@dataclass(frozen=True)
class Book:
    source_key: str
    title: str
    author: str
    publication_year: int | None


def _clean_text(value: Any, default: str, maximum_length: int = 500) -> str:
    """Convert an API value into bounded, display-safe plain text."""
    if not isinstance(value, str):
        return default
    cleaned = " ".join(value.split())
    return cleaned[:maximum_length] if cleaned else default


def normalize_books(payload: dict[str, Any]) -> list[Book]:
    """Map Open Library's response into the application's stable book schema."""
    documents = payload.get("docs")
    if not isinstance(documents, list):
        raise ValueError("Expected a JSON object with a 'docs' list")

    books: list[Book] = []
    for document in documents:
        if not isinstance(document, dict):
            continue

        source_key = _clean_text(document.get("key"), default="", maximum_length=100)
        title = _clean_text(document.get("title"), default="Untitled")
        authors = document.get("author_name", [])
        author = ", ".join(
            _clean_text(item, default="") for item in authors if isinstance(item, str)
        ) if isinstance(authors, list) else ""
        author = author or "Unknown author"

        raw_year = document.get("first_publish_year")
        year = raw_year if isinstance(raw_year, int) and 0 <= raw_year <= 2100 else None
        if source_key:
            books.append(Book(source_key, title, author[:500], year))
    return books


def fetch_books(query: str, limit: int, timeout: float = 10.0) -> list[Book]:
    """Call the public API once with a timeout and retrieve only needed fields."""
    if not query.strip():
        raise ValueError("Query must not be empty")
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")

    response = requests.get(
        SEARCH_URL,
        params={
            "q": query.strip(),
            "fields": "key,title,author_name,first_publish_year",
            "limit": limit,
        },
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Expected the API response to be a JSON object")
    return normalize_books(payload)


def save_books(database_path: str | Path, books: Iterable[Book]) -> int:
    """Upsert books by the source identifier so reruns are idempotent."""
    rows = list(books)
    retrieved_at = datetime.now(UTC).isoformat()
    connection = connect(database_path)
    try:
        create_books_table(connection)
        with transaction(connection) as cursor:
            cursor.executemany(
                """
                INSERT INTO books (source_key, title, author, publication_year, retrieved_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_key) DO UPDATE SET
                    title = excluded.title,
                    author = excluded.author,
                    publication_year = excluded.publication_year,
                    retrieved_at = excluded.retrieved_at
                """,
                [
                    (book.source_key, book.title, book.author, book.publication_year, retrieved_at)
                    for book in rows
                ],
            )
        return len(rows)
    finally:
        connection.close()


def read_books(database_path: str | Path) -> list[sqlite3.Row]:
    """Read stored data for terminal display."""
    connection = connect(database_path)
    try:
        return connection.execute(
            "SELECT title, author, publication_year FROM books ORDER BY title COLLATE NOCASE"
        ).fetchall()
    finally:
        connection.close()


def print_books(rows: Iterable[sqlite3.Row]) -> None:
    """Render a dependency-free table in the terminal."""
    rows = list(rows)
    headers = ("Title", "Author", "Year")
    values = [(row["title"], row["author"], str(row["publication_year"] or "—")) for row in rows]
    widths = [len(header) for header in headers]
    for value in values:
        widths = [max(width, len(cell)) for width, cell in zip(widths, value)]

    def line(cells: tuple[str, str, str]) -> str:
        return " | ".join(cell.ljust(width) for cell, width in zip(cells, widths))

    print(line(headers))
    print("-+-".join("-" * width for width in widths))
    for value in values:
        print(line(value))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="artificial intelligence", help="Book search query")
    parser.add_argument("--limit", type=int, default=10, help="Number of API results (1-100)")
    parser.add_argument("--db", type=Path, default=Path("data/books.db"), help="SQLite file path")
    args = parser.parse_args()

    books = fetch_books(args.query, args.limit)
    saved = save_books(args.db, books)
    print(f"Saved or updated {saved} book(s) in {args.db}.")
    print_books(read_books(args.db))


if __name__ == "__main__":
    main()