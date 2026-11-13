import pytest

from conftest import count_orders

VALID = {"customer": "Pi", "item": "keyboard", "qty": 2}


# ---------- create ----------
def test_create_order_returns_201_and_row_exists_in_db(api, db):
    r = api.post("/orders", json=VALID)
    assert r.status_code == 201
    body = r.json()
    row = db.execute("SELECT * FROM orders WHERE id = ?", (body["id"],)).fetchone()
    assert row is not None
    assert (row["customer"], row["item"], row["qty"]) == ("Pi", "keyboard", 2)
    # API response must match what is stored
    assert body["customer"] == row["customer"] and body["qty"] == row["qty"]


def test_each_order_gets_a_unique_id(api, db):
    ids = {api.post("/orders", json=VALID).json()["id"] for _ in range(5)}
    assert len(ids) == 5
    assert count_orders(db) == 5


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"item": "x", "qty": 1}, "customer"),
        ({"customer": "  ", "item": "x", "qty": 1}, "customer"),
        ({"customer": "Pi", "qty": 1}, "item"),
        ({"customer": "Pi", "item": "x"}, "qty"),
        ({"customer": "Pi", "item": "x", "qty": 0}, "qty"),
        ({"customer": "Pi", "item": "x", "qty": -3}, "qty"),
        ({"customer": "Pi", "item": "x", "qty": "2"}, "qty"),
        ({"customer": "Pi", "item": "x", "qty": True}, "qty"),
        ({"customer": "Pi", "item": "x", "qty": 1.5}, "qty"),
    ],
    ids=["no-customer", "blank-customer", "no-item", "no-qty", "zero-qty", "negative-qty", "string-qty", "bool-qty", "float-qty"],
)
def test_invalid_order_is_rejected_and_nothing_is_stored(api, db, payload, message):
    r = api.post("/orders", json=payload)
    assert r.status_code == 400
    assert message in r.json()["error"]
    assert count_orders(db) == 0  # the key DB check: a rejected request leaves no row behind


def test_malformed_json_is_rejected(api, db):
    r = api.post("/orders", data="{not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 400
    assert count_orders(db) == 0


# ---------- read ----------
def test_get_order_matches_db(api, db):
    oid = api.post("/orders", json=VALID).json()["id"]
    r = api.get(f"/orders/{oid}")
    assert r.status_code == 200
    assert r.json() == dict(db.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone())


@pytest.mark.parametrize("path", ["/orders/999999", "/orders/abc", "/nope"])
def test_missing_resources_return_404(api, path):
    assert api.get(path).status_code == 404


def test_filter_by_customer(api):
    api.post("/orders", json={**VALID, "customer": "Asha"})
    api.post("/orders", json={**VALID, "customer": "Pi"})
    api.post("/orders", json={**VALID, "customer": "Pi"})
    r = api.get("/orders", params={"customer": "Pi"})
    assert r.status_code == 200
    assert len(r.json()) == 2 and all(o["customer"] == "Pi" for o in r.json())
    assert api.get("/orders", params={"customer": "Nobody"}).json() == []


def test_list_count_matches_db_count(api, db):
    for _ in range(3):
        api.post("/orders", json=VALID)
    assert len(api.get("/orders").json()) == count_orders(db) == 3


# ---------- delete ----------
def test_delete_removes_row_from_db(api, db):
    oid = api.post("/orders", json=VALID).json()["id"]
    assert api.delete(f"/orders/{oid}").status_code == 204
    assert db.execute("SELECT 1 FROM orders WHERE id = ?", (oid,)).fetchone() is None
    assert api.get(f"/orders/{oid}").status_code == 404


def test_delete_twice_second_time_is_404(api):
    oid = api.post("/orders", json=VALID).json()["id"]
    assert api.delete(f"/orders/{oid}").status_code == 204
    assert api.delete(f"/orders/{oid}").status_code == 404


def test_delete_only_removes_the_requested_row(api, db):
    a = api.post("/orders", json=VALID).json()["id"]
    b = api.post("/orders", json=VALID).json()["id"]
    api.delete(f"/orders/{a}")
    assert count_orders(db) == 1
    assert db.execute("SELECT id FROM orders").fetchone()["id"] == b


# ---------- data safety ----------
def test_sql_injection_text_is_stored_as_plain_text(api, db):
    evil = "x'); DROP TABLE orders;--"
    r = api.post("/orders", json={**VALID, "customer": evil})
    assert r.status_code == 201
    # table still exists and the text was stored literally
    row = db.execute("SELECT customer FROM orders").fetchone()
    assert row["customer"] == evil
    assert api.get("/orders", params={"customer": evil}).json()[0]["customer"] == evil


def test_unicode_and_long_text_round_trip(api):
    text = "Pi ₹ नमस्ते 😀 " + "a" * 500
    oid = api.post("/orders", json={**VALID, "item": text}).json()["id"]
    assert api.get(f"/orders/{oid}").json()["item"] == text


def test_health_endpoint(api):
    assert api.get("/health").json() == {"status": "ok"}
