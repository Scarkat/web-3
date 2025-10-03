import pytest
import mongomock

from fastapi.testclient import TestClient 
import main

client = TestClient(main.app)  # ✅ usar main.app

fake_mongo_client = mongomock.MongoClient()
fake_database = fake_mongo_client.practica1
fake_collection_historial = fake_database.historial

@pytest.mark.parametrize(
    "numeroA, numeroB, resultado", [   # ✅ nombres consistentes
        (3, 2, 5),
        (5, 5, 10),
        (10, 15, 25)
    ]
)
def test_sumar(monkeypatch, numeroA, numeroB, resultado):
    monkeypatch.setattr(main, "collection_historial", fake_collection_historial)

    response = client.get(f"/calculadora-fast-api/sum?a={numeroA}&b={numeroB}")  # ✅ URL corregida
    assert response.status_code == 200
    assert response.json() == {"a": numeroA, "b": numeroB, "result": resultado}

def test_historial(monkeypatch):
    monkeypatch.setattr(main, "collection_historial", fake_collection_historial)

    response = client.get("/calculadora-fast-api/history")
    assert response.status_code == 200

    expected_data = list(fake_collection_historial.find({}))
    history = []
    for document in expected_data:
        history.append({
            "a": document["a"],
            "b": document["b"],
            "result": document["result"],
            "date": document["date"].isoformat()  # ✅ consistente con main.py
        })


    assert response.json() == {"history": history}
