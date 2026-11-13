"""Load test for the Orders API.

Run the API first:   python -m app.server orders.db 8000
Then (headless):     locust -f perf/locustfile.py --host http://127.0.0.1:8000 \
                          --headless -u 20 -r 5 -t 30s --csv perf/results
Or with the web UI:  locust -f perf/locustfile.py --host http://127.0.0.1:8000   (open http://localhost:8089)

User mix: browsing is more common than ordering (weights 5 : 3 : 1).
"""
import random

from locust import HttpUser, between, task


class Shopper(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.customer = f"user{random.randint(1, 50)}"
        self.my_ids = []

    @task(3)
    def place_order(self):
        with self.client.post(
            "/orders",
            json={"customer": self.customer, "item": random.choice(["pen", "book", "bag"]), "qty": random.randint(1, 5)},
            name="POST /orders",
            catch_response=True,
        ) as r:
            if r.status_code != 201:
                r.failure(f"expected 201, got {r.status_code}")
            else:
                self.my_ids.append(r.json()["id"])

    @task(5)
    def view_my_orders(self):
        self.client.get("/orders", params={"customer": self.customer}, name="GET /orders?customer")

    @task(2)
    def view_one_order(self):
        if self.my_ids:
            self.client.get(f"/orders/{random.choice(self.my_ids)}", name="GET /orders/{id}")

    @task(1)
    def cancel_order(self):
        if self.my_ids:
            oid = self.my_ids.pop()
            self.client.delete(f"/orders/{oid}", name="DELETE /orders/{id}")
