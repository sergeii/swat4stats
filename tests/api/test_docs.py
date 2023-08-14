def test_api_docs_smoke(db, client):
    response = client.get("/api/docs/")
    assert response.status_code == 200


def test_api_docs_openapi_smoke(db, api_client):
    response = api_client.get("/api/docs/?format=openapi")
    assert response.status_code == 200

    response_json = response.json()
    paths = response_json["paths"]

    assert "/servers/" in paths
    assert "/servers/{id}/" in paths
    assert "/games/" in paths
    assert "/games/{id}/" in paths
