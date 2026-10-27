"""Я связываю проверки с QA-кейсами из TEST_PLAN.md и сравниваю наблюдаемый контракт."""

import pytest
from fastapi.testclient import TestClient
from refund_api.app import create_app

pytestmark = pytest.mark.api


def refund(client, amount=3000, *, key="retry-1", currency="RUB", order_id="DEMO-1"):
    return client.post(f"/orders/{order_id}/refunds", json={"amount_minor": amount, "currency": currency},
                       headers={"Idempotency-Key": key})


def test_health_and_openapi(client):
    assert client.get("/health").json() == {"status": "ok", "version": "0.1.0"}
    schema = client.get("/openapi.json").json()
    assert set(schema["paths"]) == {"/health", "/orders", "/orders/{order_id}", "/orders/{order_id}/refunds"}
    assert client.get("/docs").status_code == 200


def test_partial_refund_contract(client, order):
    response = refund(client)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"refund_id", "order_id", "amount_minor", "currency"}
    assert body["refund_id"].startswith("RF-")
    assert (body["order_id"], body["amount_minor"], body["currency"]) == ("DEMO-1", 3000, "RUB")
    assert response.headers["Idempotency-Replayed"] == "false"
    assert client.get("/orders/DEMO-1").json() == {
        "order_id": "DEMO-1", "amount_minor": 10000, "currency": "RUB",
        "refunded_minor": 3000, "remaining_minor": 7000, "refund_count": 1,
    }


def test_exact_full_refund(client, order):
    assert refund(client, 10000).status_code == 201
    assert client.get("/orders/DEMO-1").json()["remaining_minor"] == 0
    assert refund(client, 1, key="extra").json()["error"]["code"] == "REFUND_LIMIT_EXCEEDED"


def test_repeat_does_not_double_refund(client, order):
    first = refund(client)
    second = refund(client)
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json() == second.json()
    assert second.headers["Idempotency-Replayed"] == "true"
    state = client.get("/orders/DEMO-1").json()
    assert (state["refunded_minor"], state["refund_count"]) == (3000, 1)


@pytest.mark.parametrize("change", [{"amount": 3001}, {"currency": "USD"}, {"order_id": "OTHER-1"}])
def test_key_conflicts_with_different_payload(client, order, change):
    assert refund(client).status_code == 201
    response = refund(client, **change)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert client.get("/orders/DEMO-1").json()["refunded_minor"] == 3000


def test_currency_mismatch(client, order):
    response = refund(client, currency="USD")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CURRENCY_MISMATCH"
    assert client.get("/orders/DEMO-1").json()["refund_count"] == 0


def test_excess_does_not_reserve_key(client, order):
    rejected = refund(client, 10001)
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "REFUND_LIMIT_EXCEEDED"
    assert refund(client, 10000).status_code == 201


def test_multiple_refunds_and_replay_after_exhaustion(client, order):
    first = refund(client, 3000, key="first")
    assert refund(client, 7000, key="second").status_code == 201
    repeat = refund(client, 3000, key="first")
    assert repeat.status_code == 200
    assert repeat.json() == first.json()
    state = client.get("/orders/DEMO-1").json()
    assert (state["remaining_minor"], state["refund_count"]) == (0, 2)


@pytest.mark.parametrize("amount", [0, -1, 100000001, 1.5, 100.0, "100", True, None])
def test_invalid_amounts(client, order, amount):
    response = refund(client, amount)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert client.get("/orders/DEMO-1").json()["refund_count"] == 0


@pytest.mark.parametrize("key", [None, "", "bad key", "a" * 65, "ключ"])
def test_invalid_keys(client, order, key):
    # Я передаю запрещённый алфавит байтами: так клиент не останавливает запрос
    # до API, а проверка заголовка действительно выполняется на стороне сервиса.
    headers = {} if key is None else {"Idempotency-Key": key.encode("utf-8")}
    response = client.post("/orders/DEMO-1/refunds", json={"amount_minor": 1, "currency": "RUB"}, headers=headers)
    assert response.status_code == 422
    assert client.get("/orders/DEMO-1").json()["refund_count"] == 0


@pytest.mark.parametrize("payload", [
    {"amount_minor": 1, "currency": "EUR"}, {"amount_minor": 1},
    {"amount_minor": 1, "currency": "RUB", "debug": True},
])
def test_invalid_body_contract(client, order, payload):
    response = client.post("/orders/DEMO-1/refunds", json=payload, headers={"Idempotency-Key": "new"})
    assert response.status_code == 422
    assert "input" not in str(response.json())


def test_malformed_json(client, order):
    response = client.post("/orders/DEMO-1/refunds", content=b'{"amount_minor":',
                           headers={"Content-Type": "application/json", "Idempotency-Key": "new"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_missing_order_and_wrong_method(client):
    assert client.get("/orders/MISSING").status_code == 404
    response = refund(client, order_id="MISSING")
    assert (response.status_code, response.json()["error"]["code"]) == (404, "ORDER_NOT_FOUND")
    assert client.delete("/orders/MISSING").status_code == 405


@pytest.mark.parametrize("order_id", ["bad id", "lowercase", "A" * 41, "A\n"])
def test_invalid_order_ids(client, order_id):
    response = client.post("/orders", json={"order_id": order_id, "amount_minor": 1, "currency": "RUB"})
    assert response.status_code == 422


@pytest.mark.parametrize("amount,currency", [(1, "RUB"), (100000000, "USD")])
def test_order_boundaries(client, amount, currency):
    response = client.post("/orders", json={"order_id": "EDGE", "amount_minor": amount, "currency": currency})
    assert response.status_code == 201
    assert refund(client, amount, currency=currency, order_id="EDGE").status_code == 201


def test_duplicate_order_preserves_original(client, order):
    response = client.post("/orders", json={"order_id": "DEMO-1", "amount_minor": 1, "currency": "USD"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ORDER_EXISTS"
    assert client.get("/orders/DEMO-1").json() == order


def test_restart_preserves_replay(database, client, order):
    first = refund(client)
    with TestClient(create_app(database)) as restarted:
        repeat = refund(restarted)
        assert repeat.status_code == 200
        assert repeat.json() == first.json()
        assert restarted.get("/orders/DEMO-1").json()["refunded_minor"] == 3000
