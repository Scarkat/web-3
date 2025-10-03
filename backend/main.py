import datetime
from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Literal
import math

class BatchItem(BaseModel):
    op: Literal["sum", "subtract", "multiply", "divide"]
    nums: List[float]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# MongoDB connection setup
client = MongoClient("mongodb://admin_user:web3@mongo:27017/")
database = client.practica1
collection_historial = database.historial


# --- Función auxiliar para guardar en el historial ---
def save_to_history(op: str, a: float, b: float, result: float):
    # Guardamos solo los dos primeros números en a y b para mantener el formato de la colección historial
    document = {
        "operation": op,
        "result": result,
        "a": a,
        "b": b,
        "date": datetime.datetime.now(tz=datetime.timezone.utc)
    }
    collection_historial.insert_one(document)
    
# --- Función auxiliar para operaciones batch ---
def calculate_batch_result(op: str, nums: List[float]) -> float:
    """Calcula el resultado para una operación de la lista batch."""
    
    if len(nums) < 2:
        raise HTTPException(
            status_code=400, 
            detail={"error": f"La operación '{op}' requiere al menos 2 operandos.", "operation": op, "operandos": nums}
        )
        
    if op == "sum":
        result = sum(nums)
    elif op == "multiply":
        result = math.prod(nums) # math.prod para multiplicar N números
    elif op == "subtract":
        # Resta secuencial: n1 - n2 - n3 - ...
        result = nums[0] - sum(nums[1:])
    elif op == "divide":
        # División secuencial: n1 / n2 / n3 / ...
        if 0 in nums[1:]:
             raise HTTPException(
                status_code=400, 
                detail={"error": "División por cero", "operation": "divide", "operandos": nums}
            )
        
        result = nums[0]
        for num in nums[1:]:
            result /= num
    else:
        raise HTTPException(
            status_code=400, 
            detail={"error": "Operación no soportada", "operation": op}
        )

    # Guardar en el historial (usando los primeros dos operandos para mantener el formato original)
    save_to_history(op, nums[0], nums[1], result)

    return result
    
# --- Manajedor de Errores PERSONALIZADO (se mantiene) ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == 400 and isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# --- Endpoint de Operaciones Múltiples (Batch) ---
@app.post("/calculadora-fast-api/batch_operations")
def batch_operations(items: List[BatchItem]):
    """
    Acepta una lista de operaciones y devuelve los resultados.
    """
    results = []
    
    for item in items:
        try:
            # Validación de negativos y existencia de N > 2 números
            for num in item.nums:
                if num < 0:
                    raise HTTPException(
                        status_code=400, 
                        detail={"error": f"El número {num} en la lista no puede ser negativo.", "operation": item.op, "operandos": item.nums}
                    )
            
            # Calcular el resultado usando la función auxiliar
            result_value = calculate_batch_result(item.op, item.nums)
            
            results.append({"op": item.op, "result": result_value})
            
        except HTTPException as e:
            results.append(e.detail) 
            
    return results

# --- Endpoint de Historial con Filtrado y Ordenamiento ---
@app.get("/calculadora-fast-api/history")
def obtain_history(
    operation: Optional[Literal["sum", "subtract", "multiply", "divide"]] = Query(None, description="Filtrar por tipo de operación."),
    order_by: Optional[Literal["date", "result"]] = Query("date", description="Campo para ordenar el historial."),
    sort_order: Optional[Literal["asc", "desc"]] = Query("desc", description="Orden ascendente (asc) o descendente (desc).")
):
    """
    Devuelve el historial con opciones de filtrado y ordenamiento.
    """
    
    # 1. Filtros
    query_filter = {}
    if operation:
        query_filter["operation"] = operation

    # 2. Ordenamiento
    sort_criteria = {}
    sort_direction = 1 if sort_order == "asc" else -1
    
    if order_by == "date":
        sort_criteria["date"] = sort_direction
    elif order_by == "result":
        sort_criteria["result"] = sort_direction

    # 3. Consulta a MongoDB
    records = collection_historial.find(query_filter).sort(list(sort_criteria.items())).limit(10)

    # 4. Formateo de respuesta
    history = []
    for record in records:
        op = record.get("operation", "sum") 
        history.append({
            "operation": op,
            "a": record["a"],
            "b": record["b"],
            "result": record["result"],
            "date": record["date"].isoformat()
        })

    return {"history": history}