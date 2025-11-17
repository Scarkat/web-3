from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import datetime
import logging
import os, sys
from prometheus_fastapi_instrumentator import Instrumentator
from loki_logger_handler.loki_logger_handler import LokiLoggerHandler

# -------------------------
# Logger
# -------------------------
logger = logging.getLogger("custom_logger")
logging_data = os.getenv("LOG_LEVEL", "INFO").upper()

if logging_data == "DEBUG":
    logger.setLevel(logging.DEBUG)
elif logging_data == "INFO":
    logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logger.level)
formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(name)s - %(message)s")
console_handler.setFormatter(formatter)

custom_handler = LokiLoggerHandler(
    url="http://loki:3100/loki/api/v1/push",
    labels={"application": "FastApi"},
    label_keys={},
    timeout=10,
)

logger.addHandler(console_handler)
logger.addHandler(custom_handler)
logger.info("Logger initialized")

# -------------------------
# FastAPI setup
# -------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# MongoDB
# -------------------------
client = MongoClient("mongodb://admin_user:web3@mongo:27017/")
database = client.practica1
collection_historial = database.historial

# -------------------------
# Error handling
# -------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"400 Error - Bad Request: {exc.errors()} | URL: {request.url}")
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors(), "body": exc.body},
    )

# Optional: custom handler for 400 errors in logic
from fastapi import HTTPException

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 400:
        logger.warning(f"400 Error - Bad Request: {exc.detail} | URL: {request.url}")
    else:
        logger.error(f"{exc.status_code} Error: {exc.detail} | URL: {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# -------------------------
# Routes
# -------------------------
@app.get("/calculator/sum")
def sum_numbers(a: float, b: float):
    result = a + b
    document = {
        "a": a,
        "b": b,
        "result": result,
        "date": datetime.datetime.now(tz=datetime.timezone.utc)
    }
    collection_historial.insert_one(document)
    logger.info(f"Operación suma exitosa")
    logger.debug(f"Operación suma: a={a}, b={b}, result={result}")
    return {"a": a, "b": b, "result": result}

@app.get("/calculator/divide")
def divide_numbers(a: float, b: float):
    if b == 0:
        logger.warning(f"400 Error - División por cero: a={a}, b={b}")
        raise HTTPException(status_code=400, detail="No se puede dividir entre cero.")
    
    if a < 0:
        logger.warning(f"400 Error - División con número negativo: a={a}, b={b}")
        raise HTTPException(status_code=400, detail="No se puede dividir entre números negativos.")
    
    result = a / b
    document = {
        "a": a,
        "b": b,
        "result": result,
        "date": datetime.datetime.now(tz=datetime.timezone.utc)
    }
    # collection_historial.insert_one(document)
    logger.info(f"Operación dividir exitosa")
    logger.debug(f"Operación dividir: a={a}, b={b}, result={result}")
    return {"a": a, "b": b, "result": result}

@app.get("/calculator/history")
def obtain_history():
    records = collection_historial.find().sort("date", -1).limit(10)
    history = []
    for record in records:
        history.append({
            "a": record.get("a"),
            "b": record.get("b"),
            "result": record.get("result"),
            "date": record.get("date")
        })
    logger.info("Historial recuperado")
    return {"history": history}

Instrumentator().instrument(app).expose(app)
