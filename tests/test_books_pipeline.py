from src.books_pipeline import Book, normalize_books, read_books, save_books


def test_normalize_books_keeps_valid_rows_and_safe_defaults() -> None:
    payload = {
        "docs": [
            {
                "key": "/works/OL1W",
                "title": "  Secure   Systems ",
                "author_name": ["A. Author", "B. Author"],
                "first_publish_year": 2024,
            },
            {"title": "Missing identifier"},
            {"key": "/works/OL2W", "title": None, "first_publish_year": 3000},
        ]
    }

    assert normalize_books(payload) == [
        Book("/works/OL1W", "Secure Systems", "A. Author, B. Author", 2024),
        Book("/works/OL2W", "Untitled", "Unknown author", None),
    ]


def test_save_books_is_idempotent(tmp_path) -> None:
    database = tmp_path / "books.db"
    original = Book("/works/OL1W", "First title", "Author", 2020)
    revised = Book("/works/OL1W", "Revised title", "Author", 2021)

    assert save_books(database, [original]) == 1
    assert save_books(database, [revised]) == 1
    rows = read_books(database)

    assert len(rows) == 1
    assert dict(rows[0])["title"] == "Revised title"
    assert dict(rows[0])["publication_year"] == 2021