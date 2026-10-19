def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "message": "API is running!"}


def test_readiness_check(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def _create(client, name="Docker", description=None):
    response = client.post("/items", json={"name": name, "description": description})
    assert response.status_code == 201, response.text
    return response.json()


def test_create_item(client):
    body = _create(client, "Pipeline CI/CD", "GitHub Actions")
    assert body["id"] > 0
    assert body["name"] == "Pipeline CI/CD"
    assert body["description"] == "GitHub Actions"
    assert "created_at" in body and "updated_at" in body


def test_create_item_validation(client):
    assert client.post("/items", json={}).status_code == 422
    assert client.post("/items", json={"name": ""}).status_code == 422
    assert client.post("/items", json={"name": "x" * 101}).status_code == 422


def test_list_items_with_pagination(client):
    assert client.get("/items").json() == []
    for name in ("a", "b", "c"):
        _create(client, name)

    all_items = client.get("/items").json()
    assert [i["name"] for i in all_items] == ["a", "b", "c"]

    page = client.get("/items", params={"limit": 2, "offset": 1}).json()
    assert [i["name"] for i in page] == ["b", "c"]

    assert client.get("/items", params={"limit": 0}).status_code == 422


def test_get_item(client):
    created = _create(client)
    response = client.get(f"/items/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Docker"


def test_get_item_not_found(client):
    response = client.get("/items/9999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Item não encontrado"}


def test_update_item_partial(client):
    created = _create(client, "Docker", "containers")
    response = client.patch(f"/items/{created['id']}", json={"description": "OCI"})
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Docker"  # não enviado -> não muda
    assert body["description"] == "OCI"


def test_update_item_rejects_null_name(client):
    created = _create(client)
    response = client.patch(f"/items/{created['id']}", json={"name": None})
    assert response.status_code == 422


def test_update_item_not_found(client):
    assert client.patch("/items/9999", json={"name": "x"}).status_code == 404


def test_delete_item(client):
    created = _create(client)
    response = client.delete(f"/items/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"/items/{created['id']}").status_code == 404
    assert client.delete(f"/items/{created['id']}").status_code == 404
