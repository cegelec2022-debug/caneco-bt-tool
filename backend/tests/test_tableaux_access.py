"""Acces aux endpoints tableaux (Module A) par role.

- Le chef de chantier peut LIRE la liste des tableaux et acceder aux
  fiches / QR (utile pour scanner sur chantier et imprimer les etiquettes).
- Seuls ADMIN / RA / BE proprietaire peuvent (re)generer les tableaux.

Regression : avant le fix, ``_check_project_access`` refusait le chef en
lecture, ce qui rendait la liste des tableaux toujours vide pour lui meme
quand le RA / BE avait genere les tableaux.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def project_with_tableau(db, admin_token):
    """Cree un projet + un export CANECO + une ligne 'TGBT' (style Tableau)."""
    from app.models.caneco import CanecoExport, CanecoLine
    from app.models.project import Project

    p = Project(code="TAB-ACC", name="Tableaux access", status="actif")
    db.add(p)
    db.commit()
    db.refresh(p)

    exp = CanecoExport(
        project_id=p.id,
        indice="A",
        file_name="x.xls",
        status="parsed",
        line_count=1,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)

    line = CanecoLine(
        export_id=exp.id,
        row_index=1,
        repere="TGBT",
        amont=None,
        style="Tableau",
        longueur=0.0,
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return p.id, exp.id


def test_admin_genere_les_tableaux(client, admin_headers, project_with_tableau):
    pid, eid = project_with_tableau
    resp = client.post(
        f"/api/projects/{pid}/tableaux/generate?caneco_export_id={eid}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["nb_tableaux"] >= 1


def test_chef_peut_lister_les_tableaux_apres_generation(
    client, admin_headers, chef_headers, project_with_tableau
):
    """Apres que l'admin (RA) a genere, le chef voit bien les tableaux."""
    pid, eid = project_with_tableau
    client.post(
        f"/api/projects/{pid}/tableaux/generate?caneco_export_id={eid}",
        headers=admin_headers,
    )
    resp = client.get(f"/api/projects/{pid}/tableaux", headers=chef_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1
    assert body[0]["repere"] == "TGBT"


def test_chef_ne_peut_pas_generer_les_tableaux(
    client, chef_headers, project_with_tableau
):
    pid, eid = project_with_tableau
    resp = client.post(
        f"/api/projects/{pid}/tableaux/generate?caneco_export_id={eid}",
        headers=chef_headers,
    )
    assert resp.status_code == 403


def test_chef_peut_telecharger_etiquettes_pdf(
    client, admin_headers, chef_headers, project_with_tableau
):
    """Le chef doit pouvoir imprimer la planche d'etiquettes sur chantier."""
    pid, eid = project_with_tableau
    client.post(
        f"/api/projects/{pid}/tableaux/generate?caneco_export_id={eid}",
        headers=admin_headers,
    )
    resp = client.get(
        f"/api/projects/{pid}/tableaux/labels.pdf?base_url=https://example.test",
        headers=chef_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
