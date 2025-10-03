import datetime
from fastapi import FastAPI
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware

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

@app.get("/calculadora-fast-api/sum")
def sum_numbers(a: float, b: float):
    """
    Adds two numbers passed as query parameters (?a=...&b=...)
    Example: /calculator/sum?a=1&b=2
    """
    result = a + b

    # Save to the database
    document = {
        "result": result,
        "a": a,
        "b": b,
        "date": datetime.datetime.now(tz=datetime.timezone.utc)
    }
    collection_historial.insert_one(document)

    return {"a": a, "b": b, "result": result}

@app.get("/calculadora-fast-api/history")
def obtain_history():
    """
    Returns the last 10 calculations performed.
    """
    # Fetch the last 10 records from the database, sorted by date descending
    records = collection_historial.find().sort("date", -1).limit(10)

    history = []
    for record in records:
        history.append({
            "a": record["a"],
            "b": record["b"],
            "result": record["result"],
            "date": record["date"].isoformat()  # ✅ convertir a string ISO
        })

    return {"history": history}

