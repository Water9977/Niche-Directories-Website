"""Inserts all metros.py cities (core + suburbs) into target_cities.
Idempotent — UNIQUE(city, state) means re-running is a no-op for existing rows.
"""
import sqlite3
from pathlib import Path

from metros import METROS

DB_PATH = Path(__file__).parent / "directory.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    rows = []
    for metro in METROS:
        core_city, core_state = metro["core"]
        rows.append((core_city, core_state, metro["name"]))
        for city, state in metro["suburbs"]:
            rows.append((city, state, metro["name"]))

    conn.executemany(
        "INSERT OR IGNORE INTO target_cities (city, state, metro) VALUES (?, ?, ?)",
        rows,
    )
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM target_cities").fetchone()[0]
    metros = conn.execute("SELECT COUNT(DISTINCT metro) FROM target_cities").fetchone()[0]
    print(f"Seeded. target_cities now has {total} cities across {metros} metros.")
    conn.close()


if __name__ == "__main__":
    main()
