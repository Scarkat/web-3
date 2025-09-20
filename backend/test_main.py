import pytest
import mongomock

from fastapi import FastAPI
from fastapi.testclient import TestClient 
from pymongo import MongoClient

import main

client = TestClient(main.app)
fake_mongo_client = mongomock.MongoClient()
fake_database = fake_mongo_client.practica1
fake_collection_historial = fake_database.historial

@pytest.mark.parametrize (
        "a, b, result", [
            (3, 2, 5),
            (5, 5, 10),
            (10, 15, 25)
        ]
)


def test_sumar(monkeypatch, a, b, result):
    monkeypatch.setattr(main, "collection_historial", fake_collection_historial)


    response = client.get("/calculadora-fast-api/sum?a=3&b=2")
    assert response.status_code == 200
    assert response.json() == {"a": a, "b": b, "result": result}

def test_historial(monkeypatch):
    monkeypatch.setattr(main, "collection_historial", fake_collection_historial)
    response = client.get("/calculadora-fast-api/history")
    assert response.status_code == 200

    "Obtain expected data from the collection"
    expected_data = list(fake_collection_historial.find({}))

    history = []

    for document in expected_data:
        history.append({
            "a": document["a"],
            "b": document["b"],
            "result": document["result"],
            "date": document["date"].isoformat()
        })

    print(f"DEBUG: expected_data = {history}")
    print(f"DEBUG: response.json() = {response.json()}")

    "Assert that the response data matches the expected data"
    assert response.json() == {"history": history}
