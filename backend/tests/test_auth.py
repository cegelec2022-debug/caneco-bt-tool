def test_login_valid(client, admin_token):
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@test.fr", "password": "TestPass2026!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, admin_token):
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@test.fr", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "nobody@test.fr", "password": "pass"},
    )
    assert resp.status_code == 401


def test_me_authenticated(client, admin_headers):
    resp = client.get("/api/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "admin@test.fr"
    assert data["role"] == "admin"
    assert "hashed_password" not in data


def test_me_unauthenticated(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 403


def test_register_new_user(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "be@test.fr",
            "password": "TestPass2026!",
            "full_name": "Bureau Etudes",
            "role": "BE",
        },
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_register_duplicate_email(client, admin_token):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "admin@test.fr",
            "password": "TestPass2026!",
            "full_name": "Another Admin",
            "role": "admin",
        },
    )
    assert resp.status_code == 409


def test_register_invalid_role(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "x@test.fr",
            "password": "TestPass2026!",
            "full_name": "Test",
            "role": "superadmin",
        },
    )
    assert resp.status_code == 422


def test_register_extra_field_rejected(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "extra@test.fr",
            "password": "TestPass2026!",
            "full_name": "Test",
            "role": "BE",
            "is_admin": True,
        },
    )
    assert resp.status_code == 422


def test_login_extra_field_rejected(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "x@test.fr", "password": "pass", "role": "admin"},
    )
    assert resp.status_code == 422
