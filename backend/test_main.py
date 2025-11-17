import pytest
import mongomock
import json 
from fastapi.testclient import TestClient 

import main
import datetime 

client = TestClient(main.app)
fake_mongo_client = mongomock.MongoClient()
fake_database = fake_mongo_client.practica1
fake_collection_historial = fake_database.historial

# Pruebas para la operación SUMA con N-números
@pytest.fixture(autouse=True)
def clean_mongo_mock():
    fake_collection_historial.delete_many({})

@pytest.mark.parametrize (
        "nums, expected_result", [
            ([3.0, 2.0], 5.0),       
            ([5.5, 4.5, 10.0], 20.0), 
            ([0.0, 15.0, 5.0], 20.0)
        ]
)

def test_sumar_n_numeros_exito(monkeypatch, nums, expected_result):
    monkeypatch.setattr(main, "collection_historial", fake_collection_historial)

    payload = [{"op": "sum", "nums": nums}]
    response = client.post("/calculadora-fast-api/batch_operations", json=payload)
    
    assert response.status_code == 200
    assert response.json()[0]["result"] == expected_result
    
    # Verificar que el registro se guardó en el historial.
    record = fake_collection_historial.find_one({"result": expected_result})
    assert record is not None
    assert record["operation"] == "sum"
    assert record["a"] == nums[0]
    assert record["b"] == nums[1]

#  Pruebas de VALIDACIÓN N-NÚMEROS (negativos y cero operandos).

def test_n_operaciones_error_negativos_personalizado(monkeypatch):
    """Prueba que el batch rechace números negativos con el formato de error personalizado."""
    monkeypatch.setattr(main, "collection_historial", fake_collection_historial)

    nums = [5.0, -2.0]
    payload = [{"op": "subtract", "nums": nums}]

    response = client.post("/calculadora-fast-api/batch_operations", json=payload)
    
    assert response.status_code == 200
    assert response.json()[0] == {
        "error": "El número -2.0 en la lista no puede ser negativo.", 
        "operation": "subtract", 
        "operandos": nums
    }

def test_n_operaciones_error_division_por_cero(monkeypatch):
    """Prueba que la división por cero con N números sea rechazada."""
    monkeypatch.setattr(main, "collection_historial", fake_collection_historial)
    
    nums = [10.0, 2.0, 0.0]
    payload = [{"op": "divide", "nums": nums}]
    
    response = client.post("/calculadora-fast-api/batch_operations", json=payload)
    
    assert response.status_code == 200
    assert response.json()[0] == {
        "error": "División por cero",
        "operation": "divide", 
        "operandos": nums
    }

def test_n_operaciones_error_menos_de_dos_operandos(monkeypatch):
    """Prueba que se rechace una operación con menos de dos operandos."""
    monkeypatch.setattr(main, "collection_historial", fake_collection_historial)
    
    nums = [1.0] 
    payload = [{"op": "sum", "nums": nums}]
    
    response = client.post("/calculadora-fast-api/batch_operations", json=payload)
    
    assert response.status_code == 200
    assert response.json()[0] == {
        "error": "La operación 'sum' requiere al menos 2 operandos.", 
        "operation": "sum", 
        "operandos": nums
    }


# Pruebas para BATCH OPERATIONS CON N-NÚMEROS
def test_batch_operations_n_numeros_exito(monkeypatch):
    """Prueba una lista de operaciones batch con N>2 números exitosa."""
    monkeypatch.setattr(main, "collection_historial", fake_collection_historial)
    fake_collection_historial.delete_many({})

    payload = [ 
        {"op": "sum", "nums": [5, 3, 2]},         # 10
        {"op": "multiply", "nums": [4, 2, 3]},    # 24
        {"op": "subtract", "nums": [15, 6, 1]},   # 8
        {"op": "divide", "nums": [100, 10, 2]}    # 5
    ]
    
    response = client.post("/calculadora-fast-api/batch_operations", json=payload)
    
    assert response.status_code == 200
    
    expected_output = [
        {"op": "sum", "result": 10.0},
        {"op": "multiply", "result": 24.0},
        {"op": "subtract", "result": 8.0},
        {"op": "divide", "result": 5.0}
    ]
    assert response.json() == expected_output
    
    # Verificar que el historial solo tiene 4 registros
    assert fake_collection_historial.count_documents({}) == 4

# Pruebas para BATCH OPERATIONS CON N-NÚMEROS (Errores Mixtos)
def test_batch_operations_n_numeros_con_errores(monkeypatch):
    """Prueba una lista de operaciones batch que incluye errores (negativos y división por cero)."""
    monkeypatch.setattr(main, "collection_historial", fake_collection_historial)
    fake_collection_historial.delete_many({})

    payload = [ 
        {"op": "sum", "nums": [1, 1, 1]},                # Éxito (3.0)
        {"op": "divide", "nums": [5, 0]},               # Error: División por cero
        {"op": "subtract", "nums": [10, -5, 1]},         # Error: Negativo
        {"op": "multiply", "nums": [2, 3, 4]}            # Éxito (24.0)
    ]
    
    response = client.post("/calculadora-fast-api/batch_operations", json=payload)
    
    assert response.status_code == 200
    
    expected_output = [
        {"op": "sum", "result": 3.0},
        {"error": "División por cero", "operation": "divide", "operandos": [5, 0]},
        {"error": "El número -5.0 en la lista no puede ser negativo.", "operation": "subtract", "operandos": [10, -5, 1]},
        {"op": "multiply", "result": 24.0}
    ]
    
    assert response.json()[0] == expected_output[0]
    assert response.json()[1] == expected_output[1]
    assert response.json()[2] == expected_output[2]
    assert response.json()[3] == expected_output[3]
    
    # Solo deben guardarse las 2 operaciones exitosas en el historial
    assert fake_collection_historial.count_documents({}) == 2


# Pruebas para el filtrado y ordenamiento de HISTORIAL
def test_historial_filtrado_y_ordenamiento(monkeypatch):
    """Prueba las funcionalidades de filtrado por operación y ordenamiento por resultado/fecha."""
    monkeypatch.setattr(main, "collection_historial", fake_collection_historial)
    fake_collection_historial.delete_many({})

    # 1. Insertar datos de prueba
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    fake_collection_historial.insert_many([
        {"operation": "sum", "result": 10.0, "a": 5, "b": 5, "date": now - datetime.timedelta(seconds=3)},
        {"operation": "multiply", "result": 20.0, "a": 4, "b": 5, "date": now - datetime.timedelta(seconds=2)},
        {"operation": "sum", "result": 5.0, "a": 2, "b": 3, "date": now - datetime.timedelta(seconds=1)},
        {"operation": "divide", "result": 2.5, "a": 5, "b": 2, "date": now},
    ])
    
    # Prueba 1: Filtrar por SUM y ordenar por RESULTADO descendente
    response_sum_desc = client.get("/calculadora-fast-api/history?operation=sum&order_by=result&sort_order=desc")
    history_sum_desc = response_sum_desc.json()["history"]
    
    assert response_sum_desc.status_code == 200
    assert len(history_sum_desc) == 2
    assert history_sum_desc[0]["result"] == 10.0
    assert history_sum_desc[1]["result"] == 5.0
    
    # Prueba 2: Ordenar solo por FECHA ascendente
    response_date_asc = client.get("/calculadora-fast-api/history?order_by=date&sort_order=asc")
    history_date_asc = response_date_asc.json()["history"]
    
    assert response_date_asc.status_code == 200
    assert history_date_asc[0]["result"] == 10.0
    assert history_date_asc[-1]["result"] == 2.5