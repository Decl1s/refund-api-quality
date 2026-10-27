"""Я проверяю реальные соединения SQLite, не подменяя транзакции mock-объектами."""

from concurrent.futures import ThreadPoolExecutor
import sqlite3
from threading import Barrier

from fastapi.testclient import TestClient
import pytest
from refund_api.store import Store

pytestmark = pytest.mark.concurrency


@pytest.mark.parametrize("same_key", [False, True])
def test_simultaneous_refunds(app, client, order, same_key):
    barrier = Barrier(2)

    def request(index):
        # Я синхронизирую старт, чтобы оба клиента претендовали на один остаток.
        with TestClient(app) as other:
            barrier.wait(timeout=10)
            return other.post("/orders/DEMO-1/refunds", json={"amount_minor": 7000, "currency": "RUB"},
                              headers={"Idempotency-Key": "same" if same_key else f"parallel-{index}"})

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(request, [1, 2]))
    assert sorted(r.status_code for r in results) == ([200, 201] if same_key else [201, 409])
    if same_key:
        assert results[0].json() == results[1].json()
    state = client.get("/orders/DEMO-1").json()
    assert (state["refunded_minor"], state["remaining_minor"], state["refund_count"]) == (7000, 3000, 1)


def test_busy_returns_retryable_error(database, client, order):
    blocker = sqlite3.connect(database, isolation_level=None)
    try:
        blocker.execute("BEGIN IMMEDIATE")
        response = client.post("/orders/DEMO-1/refunds", json={"amount_minor": 1, "currency": "RUB"},
                               headers={"Idempotency-Key": "retry"})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "STORE_BUSY"
        assert response.headers["Retry-After"] == "1"
    finally:
        blocker.rollback()
        blocker.close()
    assert client.get("/orders/DEMO-1").json()["refund_count"] == 0


def test_sql_failure_rolls_back_and_connection_closes(database):
    store = Store(database)
    with pytest.raises(sqlite3.IntegrityError):
        with store.connection(write=True) as con:
            con.execute("INSERT INTO orders VALUES ('ROLLBACK', 100, 'RUB')")
            con.execute("INSERT INTO refunds VALUES ('RF-X', 'key', 'MISSING', 1, 'RUB')")
    # Я проверяю эффект снаружи транзакции и возможность следующей записи.
    with sqlite3.connect(database) as con:
        assert con.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
    assert store.create_order("RECOVERED", 100, "RUB")["remaining_minor"] == 100


def test_unexpected_sql_error_is_not_reported_as_busy(database):
    store = Store(database)
    with pytest.raises(sqlite3.OperationalError):
        with store.connection(write=True) as con:
            con.execute("SELECT * FROM table_that_does_not_exist")
    assert store.create_order("AFTER-ERROR", 1, "RUB")["remaining_minor"] == 1
