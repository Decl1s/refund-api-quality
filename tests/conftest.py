"""Я выдаю каждому примеру отдельный временный SQLite-файл и закрываю клиент."""

import pytest
from fastapi.testclient import TestClient
from refund_api.app import create_app


@pytest.fixture
def database(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def app(database):
    return create_app(database)


@pytest.fixture
def client(app):
    with TestClient(app) as value:
        yield value


@pytest.fixture
def order(client):
    response = client.post("/orders", json={"order_id": "DEMO-1", "amount_minor": 10000, "currency": "RUB"})
    assert response.status_code == 201
    return response.json()
