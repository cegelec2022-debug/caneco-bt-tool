"""Tests des endpoints saisie chantier (Module B)."""

from __future__ import annotations

import pytest


@pytest.fixture
def project_with_caneco_line(db, admin_token):
    """Cree un projet + un export CANECO minimal + une ligne CANECO, retourne (project_id, line_id)."""
    from app.models.caneco import CanecoExport, CanecoLine
    from app.models.project import Project

    # Acces direct au modele (le seed normal cree DACHSER, on prefere un projet de test isole)
    project = Project(code="TEST-MOD-B", name="Test Module B", status="actif")
    db.add(project)
    db.commit()
    db.refresh(project)

    export = CanecoExport(
        project_id=project.id,
        indice="A",
        file_name="test.xls",
        status="parsed",
        line_count=1,
    )
    db.add(export)
    db.commit()
    db.refresh(export)

    line = CanecoLine(
        export_id=export.id,
        row_index=1,
        repere="D1",
        amont="TGBT",
        longueur=100.0,
        type_cable="U1000R2V",
        cable="5G6",
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return project.id, line.id


def test_upsert_field_entry_cree_la_saisie(
    client, admin_headers, project_with_caneco_line
):
    project_id, line_id = project_with_caneco_line
    resp = client.put(
        f"/api/projects/{project_id}/field-entries/{line_id}",
        json={"longueur_realisee": 105.0, "commentaire": "Detour cause IPN"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["longueur_realisee"] == 105.0
    assert body["commentaire"] == "Detour cause IPN"
    assert body["caneco_line_id"] == line_id


def test_upsert_field_entry_met_a_jour_la_saisie_existante(
    client, admin_headers, project_with_caneco_line
):
    project_id, line_id = project_with_caneco_line
    client.put(
        f"/api/projects/{project_id}/field-entries/{line_id}",
        json={"longueur_realisee": 100.0, "commentaire": None},
        headers=admin_headers,
    )
    resp = client.put(
        f"/api/projects/{project_id}/field-entries/{line_id}",
        json={"longueur_realisee": 110.0, "commentaire": "Mise a jour"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["longueur_realisee"] == 110.0
    listing = client.get(
        f"/api/projects/{project_id}/field-entries", headers=admin_headers
    ).json()
    assert len(listing) == 1  # toujours une seule saisie par ligne


def test_upsert_field_entry_refuse_longueur_negative(
    client, admin_headers, project_with_caneco_line
):
    project_id, line_id = project_with_caneco_line
    resp = client.put(
        f"/api/projects/{project_id}/field-entries/{line_id}",
        json={"longueur_realisee": -5},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_upsert_field_entry_refuse_champ_inconnu(
    client, admin_headers, project_with_caneco_line
):
    project_id, line_id = project_with_caneco_line
    resp = client.put(
        f"/api/projects/{project_id}/field-entries/{line_id}",
        json={"longueur_realisee": 100, "saisi_par": "evil-user-id"},
        headers=admin_headers,
    )
    assert resp.status_code == 422  # extra='forbid'


def test_upsert_field_entry_refuse_ligne_d_un_autre_projet(
    client, admin_headers, db
):
    """Garde-fou : on ne peut pas saisir sur une ligne CANECO d'un autre projet."""
    from app.models.caneco import CanecoExport, CanecoLine
    from app.models.project import Project

    p_legit = Project(code="LEGIT", name="Legit", status="actif")
    p_other = Project(code="OTHER", name="Other", status="actif")
    db.add_all([p_legit, p_other])
    db.commit()
    db.refresh(p_legit)
    db.refresh(p_other)

    exp = CanecoExport(
        project_id=p_other.id, indice="A", file_name="x.xls", status="parsed"
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)

    line = CanecoLine(export_id=exp.id, row_index=1, repere="X", longueur=10.0)
    db.add(line)
    db.commit()
    db.refresh(line)

    resp = client.put(
        f"/api/projects/{p_legit.id}/field-entries/{line.id}",
        json={"longueur_realisee": 50.0},
        headers=admin_headers,
    )
    assert resp.status_code == 403


def test_delete_field_entry(
    client, admin_headers, project_with_caneco_line
):
    project_id, line_id = project_with_caneco_line
    client.put(
        f"/api/projects/{project_id}/field-entries/{line_id}",
        json={"longueur_realisee": 100.0},
        headers=admin_headers,
    )
    resp = client.delete(
        f"/api/projects/{project_id}/field-entries/{line_id}", headers=admin_headers
    )
    assert resp.status_code == 204
    listing = client.get(
        f"/api/projects/{project_id}/field-entries", headers=admin_headers
    ).json()
    assert listing == []


def test_chef_de_chantier_peut_saisir_sur_un_projet_qu_il_n_a_pas_cree(
    client, db, project_with_caneco_line
):
    """En V1 le Chef de Chantier peut saisir sur tous les projets actifs."""
    project_id, line_id = project_with_caneco_line
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "chef-b@test.fr",
            "password": "TestPass2026!",
            "full_name": "Chef Test",
            "role": "chef_chantier",
        },
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    resp = client.put(
        f"/api/projects/{project_id}/field-entries/{line_id}",
        json={"longueur_realisee": 99.0, "commentaire": "Tire par mes equipes"},
        headers=h,
    )
    assert resp.status_code == 200
    assert resp.json()["longueur_realisee"] == 99.0
