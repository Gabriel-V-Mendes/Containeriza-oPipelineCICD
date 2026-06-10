from fastapi import FastAPI

app = FastAPI(title="DevOps API")

fake_db = [{"item_name": "Docker"}, {"item_name": "FastAPI"}]

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is running!"}

@app.get("/items")
def read_items():
    return fake_db

@app.post("/items")
def create_item(item: dict):
    fake_db.append(item)
    return {"message": "Item added", "item": item}
