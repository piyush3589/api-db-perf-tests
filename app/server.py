"""Tiny Orders API (stdlib + SQLite). This is the system under test for the demo.

POST   /orders        {"customer": str, "item": str, "qty": int>0}  -> 201 + order
GET    /orders        ?customer=<name>                              -> 200 list
GET    /orders/{id}                                                 -> 200 | 404
DELETE /orders/{id}                                                 -> 204 | 404
GET    /health                                                      -> 200
"""
import json
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SCHEMA = """CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer TEXT NOT NULL,
    item TEXT NOT NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)"""


def init_db(path):
    with sqlite3.connect(path) as db:
        db.execute(SCHEMA)


def make_handler(db_path):
    class Handler(BaseHTTPRequestHandler):
        def _db(self):
            db = sqlite3.connect(db_path, timeout=10)
            db.row_factory = sqlite3.Row
            return db

        def _send(self, status, payload=None):
            body = b"" if payload is None else json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _order_id(self):
            m = re.fullmatch(r"/orders/(\d+)", urlparse(self.path).path)
            return int(m.group(1)) if m else None

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/health":
                return self._send(200, {"status": "ok"})
            if url.path == "/orders":
                customer = parse_qs(url.query).get("customer", [None])[0]
                with self._db() as db:
                    if customer is None:
                        rows = db.execute("SELECT * FROM orders ORDER BY id").fetchall()
                    else:
                        rows = db.execute("SELECT * FROM orders WHERE customer = ? ORDER BY id", (customer,)).fetchall()
                return self._send(200, [dict(r) for r in rows])
            oid = self._order_id()
            if oid is None:
                return self._send(404, {"error": "not found"})
            with self._db() as db:
                row = db.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()
            return self._send(200, dict(row)) if row else self._send(404, {"error": "order not found"})

        def do_POST(self):
            if urlparse(self.path).path != "/orders":
                return self._send(404, {"error": "not found"})
            try:
                length = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(length) or b"{}")
            except (ValueError, json.JSONDecodeError):
                return self._send(400, {"error": "invalid JSON"})
            customer, item, qty = data.get("customer"), data.get("item"), data.get("qty")
            if not isinstance(customer, str) or not customer.strip():
                return self._send(400, {"error": "customer is required"})
            if not isinstance(item, str) or not item.strip():
                return self._send(400, {"error": "item is required"})
            if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
                return self._send(400, {"error": "qty must be a positive integer"})
            with self._db() as db:
                cur = db.execute("INSERT INTO orders (customer, item, qty) VALUES (?, ?, ?)", (customer, item, qty))
                row = db.execute("SELECT * FROM orders WHERE id = ?", (cur.lastrowid,)).fetchone()
            return self._send(201, dict(row))

        def do_DELETE(self):
            oid = self._order_id()
            if oid is None:
                return self._send(404, {"error": "not found"})
            with self._db() as db:
                cur = db.execute("DELETE FROM orders WHERE id = ?", (oid,))
            return self._send(204) if cur.rowcount else self._send(404, {"error": "order not found"})

        def log_message(self, *args):
            pass

    return Handler


def start(db_path, host="127.0.0.1", port=0):
    init_db(db_path)
    server = ThreadingHTTPServer((host, port), make_handler(db_path))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://{host}:{server.server_address[1]}"


if __name__ == "__main__":
    import sys
    db = sys.argv[1] if len(sys.argv) > 1 else "orders.db"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    s, url = start(db, port=port)
    print("Orders API on", url, "db:", db)
    threading.Event().wait()
