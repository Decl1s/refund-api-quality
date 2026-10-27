"""Я показываю сценарий без постоянного сервера и без сохранения БД."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from refund_api.app import create_app


def main():
    with TemporaryDirectory() as folder, TestClient(create_app(Path(folder) / "demo.db")) as client:
        order = client.post("/orders", json={"order_id": "DEMO-1", "amount_minor": 10000, "currency": "RUB"})
        assert order.status_code == 201
        for key, amount in [("first", 3000), ("first", 3000), ("excess", 8000), ("last", 7000)]:
            response = client.post("/orders/DEMO-1/refunds", json={"amount_minor": amount, "currency": "RUB"},
                                   headers={"Idempotency-Key": key})
            print(f"key={key}, amount_minor={amount} -> HTTP {response.status_code}")
            print(response.json())
        state = client.get("/orders/DEMO-1").json()
        assert (state["remaining_minor"], state["refund_count"]) == (0, 2)
        print("Я завершил demo:", state)


if __name__ == "__main__":
    main()
