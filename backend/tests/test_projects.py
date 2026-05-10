def test_list_projects_unauthenticated(client):
    resp = client.get("/api/projects/")
    assert resp.status_code == 403


def test_list_projects_empty(client, admin_headers):
    resp = client.get("/api/projects/", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_project(client, admin_headers):
    resp = client.post(
        "/api/projects/",
        json={"code": "TEST-001", "name": "Projet Test", "client": "Client SA"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "TEST-001"
    assert data["name"] == "Projet Test"
    assert data["client"] == "Client SA"
    assert "id" in data


def test_create_project_duplicate_code(client, admin_headers):
    client.post(
        "/api/projects/",
        json={"code": "DUP-001", "name": "Premier"},
        headers=admin_headers,
    )
    resp = client.post(
        "/api/projects/",
        json={"code": "DUP-001", "name": "Doublon"},
        headers=admin_headers,
    )
    assert resp.status_code == 409


def test_create_project_extra_field_rejected(client, admin_headers):
    resp = client.post(
        "/api/projects/",
        json={"code": "X-001", "name": "Test", "created_by": "hacker-id"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_get_project(client, admin_headers):
    create_resp = client.post(
        "/api/projects/",
        json={"code": "GET-001", "name": "Projet Get"},
        headers=admin_headers,
    )
    project_id = create_resp.json()["id"]
    resp = client.get(f"/api/projects/{project_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == "GET-001"


def test_get_project_not_found(client, admin_headers):
    resp = client.get("/api/projects/nonexistent-id", headers=admin_headers)
    assert resp.status_code == 404


def test_update_project(client, admin_headers):
    create_resp = client.post(
        "/api/projects/",
        json={"code": "UPD-001", "name": "Ancien nom"},
        headers=admin_headers,
    )
    project_id = create_resp.json()["id"]
    resp = client.patch(
        f"/api/projects/{project_id}",
        json={"name": "Nouveau nom", "status": "archivé"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Nouveau nom"
    assert data["status"] == "archivé"


def test_delete_project(client, admin_headers):
    create_resp = client.post(
        "/api/projects/",
        json={"code": "DEL-001", "name": "A supprimer"},
        headers=admin_headers,
    )
    project_id = create_resp.json()["id"]
    resp = client.delete(f"/api/projects/{project_id}", headers=admin_headers)
    assert resp.status_code == 204
    get_resp = client.get(f"/api/projects/{project_id}", headers=admin_headers)
    assert get_resp.status_code == 404


def test_be_cannot_see_others_projects(client, admin_headers, be_headers):
    client.post(
        "/api/projects/",
        json={"code": "ADMIN-001", "name": "Projet Admin"},
        headers=admin_headers,
    )
    resp = client.get("/api/projects/", headers=be_headers)
    assert resp.status_code == 200
    # BE user has no own projects — should see empty list
    assert resp.json() == []


def test_be_cannot_access_others_project(client, admin_headers, be_headers):
    create_resp = client.post(
        "/api/projects/",
        json={"code": "PRIV-001", "name": "Projet Privé"},
        headers=admin_headers,
    )
    project_id = create_resp.json()["id"]
    resp = client.get(f"/api/projects/{project_id}", headers=be_headers)
    assert resp.status_code == 403


def test_admin_sees_all_projects(client, admin_headers, be_headers):
    client.post(
        "/api/projects/",
        json={"code": "BE-001", "name": "Projet BE"},
        headers=be_headers,
    )
    resp = client.get("/api/projects/", headers=admin_headers)
    assert resp.status_code == 200
    codes = [p["code"] for p in resp.json()]
    assert "BE-001" in codes
