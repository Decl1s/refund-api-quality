"""Я проверяю денежный инвариант независимой моделью последовательности запросов."""

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st
import pytest
from refund_api.app import create_app

pytestmark = pytest.mark.property


@settings(max_examples=40, derandomize=True, database=None, deadline=None)
@given(paid=st.integers(1, 100000), amounts=st.lists(st.integers(1, 100000), min_size=1, max_size=8))
def test_refund_sequence_matches_independent_model(paid, amounts):
    # Я создаю БД внутри каждого Hypothesis-примера: fixture scope одного теста
    # здесь ошибочно смешал бы состояние нескольких сгенерированных сценариев.
    with TemporaryDirectory() as folder, TestClient(create_app(Path(folder) / "state.db")) as client:
        assert client.post("/orders", json={"order_id": "MODEL", "amount_minor": paid, "currency": "RUB"}).status_code == 201
        remaining, count = paid, 0
        for index, amount in enumerate(amounts):
            payload = {"amount_minor": amount, "currency": "RUB"}
            headers = {"Idempotency-Key": f"model-{index}"}
            response = client.post("/orders/MODEL/refunds", json=payload, headers=headers)
            if amount <= remaining:
                assert response.status_code == 201
                remaining -= amount
                count += 1
                repeated = client.post("/orders/MODEL/refunds", json=payload, headers=headers)
                assert repeated.status_code == 200
                assert repeated.json() == response.json()
            else:
                assert response.status_code == 409
                assert response.json()["error"]["code"] == "REFUND_LIMIT_EXCEEDED"
            state = client.get("/orders/MODEL").json()
            assert (state["remaining_minor"], state["refunded_minor"], state["refund_count"]) == (remaining, paid - remaining, count)
            assert 0 <= state["refunded_minor"] <= paid
