# API + Database Testing and Load Testing (Python)

Two QA skills in one repo, on a small Orders API (`app/server.py`, stdlib + SQLite) that I wrote as a test target:

1. **API + DB tests (pytest):** every API call is checked *and* the database is inspected directly, so the tests prove data was really stored, changed, deleted, or **not** stored when a request is rejected.
2. **Load test (Locust):** a realistic user mix hits the API, and a threshold script fails the run when response time or error rate break agreed limits.

## What the 24 tests cover

| Area | Examples |
|---|---|
| Create | 201 + row exists in DB, API response equals stored row, unique IDs |
| Validation (parametrized) | missing/blank customer, missing item, qty missing / 0 / negative / string / bool / float, malformed JSON. Each asserts **400 and zero rows stored** |
| Read | GET by id equals DB row, 404 for missing/non-numeric ids and unknown paths, filter by customer, list count equals DB count |
| Delete | row really gone from DB, second delete is 404, only the requested row is removed |
| Data safety | SQL-injection text stored as plain text and table survives, unicode and 500-char text round trip |

## Run it

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

pytest                                                # API + DB tests (starts its own server and temp DB)

# Load test
python -m app.server orders.db 8000                   # terminal 1: start the API
locust -f perf/locustfile.py --host http://127.0.0.1:8000 \
       --headless -u 20 -r 10 -t 30s --csv perf/results      # terminal 2
python perf/check_thresholds.py perf/results_stats.csv --p95-ms 500 --max-fail-pct 1
# or use Locust's web UI: drop --headless and open http://localhost:8089
```

## Design notes

- **Why inspect the DB?** A 201 response only says the server *claims* it saved the data. Reading the table independently catches "returned success but stored nothing" and "returned an error but still stored a row".
- **Tests are independent:** the table is emptied before each test.
- **Mutation check:** I broke the API on purpose (allowed qty 0, delete wiped every row, built SQL by string formatting). The tests failed on each, so they detect real bugs.
- **Load test mix:** 5 browse : 3 order : 2 view : 1 cancel, closer to real use than hammering one endpoint.
- **Limits of the load numbers:** the API runs on the same machine as Locust, so the numbers (a few ms) show that the setup works, **not** how a production system would perform. Use the tooling against a real staging URL for real results.

## Possible next steps

- Run against Postgres in Docker instead of SQLite
- Add `PUT /orders/{id}` and update tests
- Ramp-up / spike / soak load profiles and a Locust HTML report (`--html report.html`)
