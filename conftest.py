"""Fixtures: start the demo API on a temp SQLite file and give tests both an HTTP client and a DB connection.

The point of this project: after each API call we also look INSIDE the database
(`db` fixture) to prove the data really was stored / not stored.
"""
import sqlite3

import pytest
import requests

from app.server import start


@pytest.fixture(scope="session")
def _server(tmp_path_factory):
    db_path = str(tmp_path_factory.mktemp("db") / "orders.db")
    server, url = start(db_path)
    yield db_path, url
    server.shutdown()


@pytest.fixture
def base_url(_server):
    return _server[1]


@pytest.fixture
def db(_server):
    """Direct DB connection. Table is emptied before every test so tests do not affect each other."""
    conn = sqlite3.connect(_server[0])
    conn.row_factory = sqlite3.Row
    conn.execute("DELETE FROM orders")
    conn.commit()
    yield conn
    conn.close()


class Api(requests.Session):
    def __init__(self, base):
        super().__init__()
        self.base = base

    def request(self, method, url, **kw):
        kw.setdefault("timeout", 10)
        return super().request(method, self.base + url, **kw)


@pytest.fixture
def api(base_url, db):  # depends on db so the table is clean first
    return Api(base_url)


def count_orders(db) -> int:
    return db.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
