def test_motd_summary(db, client):
    response = client.get("/api/motd/summary/")
    assert response.status_code == 200
    assert response.content == b""
