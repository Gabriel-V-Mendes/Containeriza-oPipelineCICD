from fastapi.testclient import TestClient
from app.main import app

# O TestClient simula requisições reais para a nossa API
client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "message": "API is running!"}

def test_read_items():
    response = client.get("/items")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_item():
    new_item = {"item_name": "Pipeline CI/CD"}
    response = client.post("/items", json=new_item)
    assert response.status_code == 200
    assert response.json()["item"]["item_name"] == "Pipeline CI/CD"