"""Labels each raw_listing's geo_status against its assigned target_city.

Per the brief: mismatched-city listings get labeled, not silently dropped —
export_json's quality gate decides what actually gets published. A business
in Kannapolis that turned up under a Concord search is real data, just
possibly the wrong page to list it on.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "directory.db"


def main():
    conn = sqlite3.connect(DB_PATH)

    confirmed = conn.execute(
        """
        UPDATE raw_listings SET geo_status = 'confirmed'
        WHERE city IS NOT NULL AND target_city_id IN (
            SELECT id FROM target_cities tc WHERE LOWER(tc.city) = LOWER(raw_listings.city)
        )
        """
    )
    mismatch = conn.execute(
        """
        UPDATE raw_listings SET geo_status = 'mismatch'
        WHERE city IS NOT NULL AND target_city_id NOT IN (
            SELECT id FROM target_cities tc WHERE LOWER(tc.city) = LOWER(raw_listings.city)
        )
        """
    )
    unknown = conn.execute("UPDATE raw_listings SET geo_status = 'unknown' WHERE city IS NULL")
    conn.commit()

    counts = conn.execute(
        "SELECT geo_status, COUNT(*) FROM raw_listings GROUP BY geo_status"
    ).fetchall()
    print("geo_status breakdown:", dict(counts))

    print("\nMismatches (real business, wrong target city page):")
    for row in conn.execute(
        """
        SELECT rl.name, rl.city, tc.city FROM raw_listings rl
        JOIN target_cities tc ON rl.target_city_id = tc.id
        WHERE rl.geo_status = 'mismatch'
        """
    ):
        print(" -", row[0], "| actual city:", row[1], "| searched under:", row[2])

    conn.close()


if __name__ == "__main__":
    main()
