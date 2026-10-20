"""Seed a dummy SQLite store: 100 customers with addresses and orders.

Deterministic (fixed Faker seed) so every run produces the same database. The data is
synthetic; no real people. Used by the demo agent's PII tools.
"""

from __future__ import annotations

import pathlib
import sqlite3

from faker import Faker

DB = pathlib.Path(__file__).resolve().parent / "data" / "customers.db"
DB.parent.mkdir(parents=True, exist_ok=True)

fake = Faker()
Faker.seed(42)

SCHEMA = """
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS addresses;
DROP TABLE IF EXISTS orders;
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT);
CREATE TABLE addresses (customer_id INTEGER, line1 TEXT, city TEXT, region TEXT,
                        postal TEXT, country TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, item TEXT,
                     amount REAL, status TEXT, ordered_at TEXT);
"""

ITEMS = [
    "Standing desk",
    "Mechanical keyboard",
    "Noise-cancelling headphones",
    "4K monitor",
    "Webcam",
    "USB-C dock",
    "Ergonomic chair",
    "Laptop stand",
]
STATUSES = ["delivered", "shipped", "processing", "returned", "cancelled"]


def main() -> None:
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)
    order_id = 1000
    for cid in range(1, 101):
        name = fake.name()
        conn.execute(
            "INSERT INTO customers VALUES (?,?,?,?)",
            (cid, name, fake.email(), fake.phone_number()),
        )
        conn.execute(
            "INSERT INTO addresses VALUES (?,?,?,?,?,?)",
            (cid, fake.street_address(), fake.city(), fake.state_abbr(), fake.postcode(), "USA"),
        )
        for _ in range(fake.random_int(1, 3)):
            order_id += 1
            conn.execute(
                "INSERT INTO orders VALUES (?,?,?,?,?,?)",
                (
                    order_id,
                    cid,
                    fake.random_element(ITEMS),
                    round(fake.random_int(2000, 60000) / 100, 2),
                    fake.random_element(STATUSES),
                    fake.date_time_this_year().isoformat(timespec="seconds"),
                ),
            )
    conn.commit()
    c = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    o = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    conn.close()
    print(f"seeded {DB} with {c} customers and {o} orders")


if __name__ == "__main__":
    main()
