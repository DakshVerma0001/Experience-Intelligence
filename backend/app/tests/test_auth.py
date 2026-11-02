def test_login_success(client):
    resp = client.post("/api/auth/login", json={"email": "admin@test.example", "password": "Password123!"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "ADMIN"
    assert "access_token" in data


def test_login_wrong_password(client):
    resp = client.post("/api/auth/login", json={"email": "admin@test.example", "password": "wrong"})
    assert resp.status_code == 401


def test_me_requires_auth(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_token(client, contributor_headers):
    resp = client.get("/api/auth/me", headers=contributor_headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "CONTRIBUTOR"


def test_contributor_cannot_access_admin_routes(client, contributor_headers):
    resp = client.get("/api/audit/logs", headers=contributor_headers)
    assert resp.status_code == 403


def test_admin_can_list_users(client, admin_headers):
    resp = client.get("/api/auth/users", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 3
