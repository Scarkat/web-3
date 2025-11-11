# import datetime, os, sys, logging
# from fastapi import FastAPI
# from pymongo import MongoClient
# from fastapi.middleware.cors import CORSMiddleware
# from prometheus_fastapi_instrumentator import Instrumentator
# from loki_logger_handler.handler import LokiLoggerHandler

# app = FastAPI()

# # set logging xddd aaaaaaagria
# logger = logging.getLogger("custom_logger")
# logging_data = os.getenv("LOG_LEVEL", "INFO").upper()

# if logging_data == "DEBUG":
#     logger.setLevel(logging.DEBUG)
# else:
#     logger.setLevel(logging.INFO)

# # set handler
# console_handler = logging.StreamHandler(sys.stdout)
# console_handler.setLevel(logger.level)
# formatter = logging.Formatter(
#     "%(levelname)s: %(asctime)s - %(name)s - %(message)s"
# )
# console_handler.setFormatter(formatter)

# # Create an instance of the custom handler
# loki_handler = LokiLoggerHandler(
#     url="http://loki:3100/loki/api/v1/push",
#     labels={"application": "FastApi"},
#     label_keys={},
#     timeout=10,
# )

# logger.addHandler(loki_handler)
# logger.addHandler(console_handler)
# logger.info("Logger initialized")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"]
# )

# # MongoDB connection setup
# client = MongoClient("mongodb://admin_user:web3@mongo:27017/")
# database = client.practica1
# collection_historial = database.historial
# saludo = "hola mundo!"

# def imprimir_saludo():
#     print(saludo)
#     print("Imprimiendo saludo desde main.py")

# @app.get("/calculadora-fast-api/sum")
# def sum_numbers(a: float, b: float):
#     """
#     Adds two numbers passed as query parameters (?a=...&b=...)
#     Example: /calculator/sum?a=1&b=2
#     """
#     result = a + b

#     # Save to the database
#     document = {
#         "result": result,
#         "a": a,
#         "b": b,
#         "date": datetime.datetime.now(tz=datetime.timezone.utc)
#     }

#     logger.info(f"Operación suma exitoso")
#     logger.debug(f"Operación suma: a={a}, b={b}, resultado={result}")

#     collection_historial.insert_one(document)

#     return {"a": a, "b": b, "result": result}

# @app.get("/calculadora-fast-api/history")
# def obtain_history():
#     """
#     Returns the last 10 calculations performed.
#     """
#     # Fetch the last 10 records from the database, sorted by date descending
#     records = collection_historial.find().sort("date", -1).limit(10)

#     history = []
#     for record in records:
#         history.append({
#             "a": record["a"],
#             "b": record["b"],
#             "result": record["result"],
#             "date": record["date"].isoformat()  # ✅ convertir a string ISO
#         })

#     return {"history": history}

# Instrumentator().instrument(app).expose(app)

import logging
import sys
import os
import datetime
from fastapi import FastAPI
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

# ===== LOGGING =====
logger = logging.getLogger("custom_logger")
logging_level = os.getenv("LOG_LEVEL", "INFO").upper()
logger.setLevel(logging_level)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging_level)
formatter = logging.Formatter(
    "%(levelname)s: %(asctime)s - %(name)s - %(message)s"
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== PROMETHEUS =====
Instrumentator().instrument(app).expose(app)

# ===== MONGODB =====
mongo_uri = os.getenv("MONGO_URI", "mongodb://admin_user:web3@mongo:27017/practica1?authSource=admin")
mongo_client = MongoClient(mongo_uri)
database = mongo_client["practica1"]
collection_historial = database["historial"]

# ===== ENDPOINTS =====
@app.get("/calculadora-fast-api/sum")
async def sum_numbers(a: int, b: int):
    result = a + b
    collection_historial.insert_one({
        "a": a,
        "b": b,
        "result": result,
        "date": datetime.datetime.now()
    })
    logger.info(f"Sum: {a} + {b} = {result}")
    return {"a": a, "b": b, "result": result}

@app.get("/calculadora-fast-api/history")
async def obtain_history():
    history = list(collection_historial.find({}))
    history_formatted = []
    for doc in history:
        history_formatted.append({
            "a": doc["a"],
            "b": doc["b"],
            "result": doc["result"],
            "date": str(doc["date"])
        })
    return {"history": history_formatted}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
