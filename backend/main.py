import datetime
import math
import os
import sys
import logging
from typing import List, Optional, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator
from loki_logger_handler.loki_logger_handler import LokiLoggerHandler

# ----------------------------
# App, CORS, DB (Mongo)
# ----------------------------
app = FastAPI(title="Calculadora - Parcial Integrador")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin_user:web3@mongo:27017/")
client = MongoClient(MONGO_URI)
database = client.practica1
collection_historial = database.historial

# ----------------------------
# Logging (console + Loki)
# ----------------------------
logger = logging.getLogger("calculadora")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger.setLevel(LOG_LEVEL)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logger.level)
fmt = logging.Formatter("%(levelname)s: %(asctime)s - %(name)s - %(message)s")
console_handler.setFormatter(fmt)
logger.addHandler(console_handler)

# Loki handler
LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100/loki/api/v1/push")
try:
    loki_handler = LokiLoggerHandler(
        url=LOKI_URL,
        labels={"application": "FastApi", "service": "calculadora"},
        label_keys={},
        timeout=10,
    )
    loki_handler.setLevel(logger.level)
    logger.addHandler(loki_handler)
except Exception as e:
    # If the handler fails to initialize (e.g., missing package), keep going but log locally.
    logger.warning("No se pudo inicializar LokiLoggerHandler: %s", e)

logger.info("Logger initialized (level=%s)", LOG_LEVEL)

# ----------------------------
# Prometheus metrics
# ----------------------------
OPERATION_COUNTER = Counter(
    "calculator_operations_total", "Total number of calculator operations", ["operation"]
)
OPERATION_ERRORS = Counter(
    "calculator_operation_errors_total", "Total number of errors per operation", ["operation"]
)
OPERATION_DURATION = Histogram(
    "calculator_operation_duration_seconds", "Duration of calculator operations", ["operation"]
)

# Instrumentator for common metrics & /metrics endpoint
Instrumentator().instrument(app).expose(app)

# ----------------------------
# Models
# ----------------------------
class BatchItem(BaseModel):
    op: Literal["sum", "subtract", "multiply", "divide"]
    nums: List[float]


# ----------------------------
# Utilities: history and save
# ----------------------------
def save_to_history(op: str, a: float, b: float, result: float):
    document = {
        "operation": op,
        "result": result,
        "a": a,
        "b": b,
        "date": datetime.datetime.now(tz=datetime.timezone.utc),
    }
    try:
        collection_historial.insert_one(document)
    except Exception as e:
        # If DB fails, log error but do not raise internal server error for the caller
        logger.error("Error guardando historial en Mongo: %s", e)
        # Optionally increment a DB error metric here in the future


# ----------------------------
# Error handler (consistent response + logging)
# ----------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Log the error with details
    logger.error(
        "HTTPException - path=%s status=%s detail=%s",
        request.url.path,
        exc.status_code,
        exc.detail,
    )
    # If the exception has structured detail, return it; else wrap it
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# ----------------------------
# Operation helpers
# ----------------------------
def validate_no_negatives(nums: List[float], op_name: str):
    for n in nums:
        if n < 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"El número {n} no puede ser negativo para la operación '{op_name}'.",
                    "operation": op_name,
                    "operandos": nums,
                },
            )


def calculate_operation(op: str, a: float, b: float) -> float:
    if op == "sum":
        return a + b
    if op == "subtract":
        return a - b
    if op == "multiply":
        return a * b
    if op == "divide":
        if b == 0:
            raise HTTPException(
                status_code=400,
                detail={"error": "División por cero", "operation": "divide", "operandos": [a, b]},
            )
        return a / b
    raise HTTPException(status_code=400, detail={"error": "Operación no soportada", "operation": op})


def calculate_batch_result(op: str, nums: List[float]) -> float:
    if len(nums) < 2:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"La operación '{op}' requiere al menos 2 operandos.",
                "operation": op,
                "operandos": nums,
            },
        )

    if op == "sum":
        result = sum(nums)
    elif op == "multiply":
        result = math.prod(nums)
    elif op == "subtract":
        result = nums[0] - sum(nums[1:])
    elif op == "divide":
        if 0 in nums[1:]:
            raise HTTPException(
                status_code=400,
                detail={"error": "División por cero en batch", "operation": "divide", "operandos": nums},
            )
        result = nums[0]
        for num in nums[1:]:
            result /= num
    else:
        raise HTTPException(status_code=400, detail={"error": "Operación no soportada", "operation": op})

    # Save to history using first two operands (compatibility with existing schema)
    save_to_history(op, nums[0], nums[1], result)
    return result


# ----------------------------
# Individual operation endpoints
# ----------------------------
@app.get("/calculadora-fast-api/sum")
def sum_numbers(a: float = Query(...), b: float = Query(...)):
    op = "sum"
    OPERATION_COUNTER.labels(op).inc()
    with OPERATION_DURATION.labels(op).time():
        try:
            validate_no_negatives([a, b], op)
            result = calculate_operation(op, a, b)
            save_to_history(op, a, b, result)
            logger.info("Operación %s exitosa: a=%s b=%s result=%s", op, a, b, result)
            return {"a": a, "b": b, "result": result}
        except HTTPException:
            OPERATION_ERRORS.labels(op).inc()
            raise
        except Exception as e:
            OPERATION_ERRORS.labels(op).inc()
            logger.exception("Error inesperado en %s: %s", op, e)
            raise HTTPException(status_code=500, detail={"error": "Error interno", "message": str(e)})


@app.get("/calculadora-fast-api/subtract")
def subtract_numbers(a: float = Query(...), b: float = Query(...)):
    op = "subtract"
    OPERATION_COUNTER.labels(op).inc()
    with OPERATION_DURATION.labels(op).time():
        try:
            validate_no_negatives([a, b], op)
            result = calculate_operation(op, a, b)
            save_to_history(op, a, b, result)
            logger.info("Operación %s exitosa: a=%s b=%s result=%s", op, a, b, result)
            return {"a": a, "b": b, "result": result}
        except HTTPException:
            OPERATION_ERRORS.labels(op).inc()
            raise
        except Exception as e:
            OPERATION_ERRORS.labels(op).inc()
            logger.exception("Error inesperado en %s: %s", op, e)
            raise HTTPException(status_code=500, detail={"error": "Error interno", "message": str(e)})


@app.get("/calculadora-fast-api/multiply")
def multiply_numbers(a: float = Query(...), b: float = Query(...)):
    op = "multiply"
    OPERATION_COUNTER.labels(op).inc()
    with OPERATION_DURATION.labels(op).time():
        try:
            validate_no_negatives([a, b], op)
            result = calculate_operation(op, a, b)
            save_to_history(op, a, b, result)
            logger.info("Operación %s exitosa: a=%s b=%s result=%s", op, a, b, result)
            return {"a": a, "b": b, "result": result}
        except HTTPException:
            OPERATION_ERRORS.labels(op).inc()
            raise
        except Exception as e:
            OPERATION_ERRORS.labels(op).inc()
            logger.exception("Error inesperado en %s: %s", op, e)
            raise HTTPException(status_code=500, detail={"error": "Error interno", "message": str(e)})


@app.get("/calculadora-fast-api/divide")
def divide_numbers(a: float = Query(...), b: float = Query(...)):
    op = "divide"
    OPERATION_COUNTER.labels(op).inc()
    with OPERATION_DURATION.labels(op).time():
        try:
            validate_no_negatives([a, b], op)
            result = calculate_operation(op, a, b)
            save_to_history(op, a, b, result)
            logger.info("Operación %s exitosa: a=%s b=%s result=%s", op, a, b, result)
            return {"a": a, "b": b, "result": result}
        except HTTPException:
            OPERATION_ERRORS.labels(op).inc()
            raise
        except Exception as e:
            OPERATION_ERRORS.labels(op).inc()
            logger.exception("Error inesperado en %s: %s", op, e)
            raise HTTPException(status_code=500, detail={"error": "Error interno", "message": str(e)})


# ----------------------------
# Batch endpoint
# ----------------------------
@app.post("/calculadora-fast-api/batch_operations")
def batch_operations(items: List[BatchItem]):
    results = []
    for item in items:
        op = item.op
        OPERATION_COUNTER.labels(op).inc()
        with OPERATION_DURATION.labels(op).time():
            try:
                validate_no_negatives(item.nums, op)
                result_value = calculate_batch_result(op, item.nums)
                logger.info("Batch op %s exitosa: nums=%s result=%s", op, item.nums, result_value)
                results.append({"op": op, "result": result_value})
            except HTTPException as he:
                OPERATION_ERRORS.labels(op).inc()
                logger.warning("Batch op %s falló: %s", op, he.detail)
                results.append(he.detail)
            except Exception as e:
                OPERATION_ERRORS.labels(op).inc()
                logger.exception("Error inesperado en batch op %s: %s", op, e)
                results.append({"error": "Error interno", "message": str(e)})
    return results


# ----------------------------
# History endpoint with filters and ordering
# ----------------------------
@app.get("/calculadora-fast-api/history")
def obtain_history(
    operation: Optional[Literal["sum", "subtract", "multiply", "divide"]] = Query(None),
    order_by: Optional[Literal["date", "result"]] = Query("date"),
    sort_order: Optional[Literal["asc", "desc"]] = Query("desc"),
):
    # Filters
    query_filter = {}
    if operation:
        query_filter["operation"] = operation

    # Sorting
    sort_direction = 1 if sort_order == "asc" else -1
    if order_by == "date":
        sort_field = "date"
    else:
        sort_field = "result"

    records = collection_historial.find(query_filter).sort(sort_field, sort_direction).limit(10)

    history = []
    for record in records:
        history.append(
            {
                "operation": record.get("operation", "sum"),
                "a": record["a"],
                "b": record["b"],
                "result": record["result"],
                "date": record["date"].isoformat(),
            }
        )

    logger.debug("Historial consultado: filter=%s order_by=%s sort_order=%s", query_filter, order_by, sort_order)
    return {"history": history}
