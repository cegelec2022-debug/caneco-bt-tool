"""Tests du tableau de bord RA (Module C)."""

from __future__ import annotations


def test_dashboard_reserve_ra_admin(client, db, be_headers):
    """Le BE n'a pas acces au tableau de bord."""
    resp = client.get("/api/dashboard/summary", headers=be_headers)
    assert resp.status_code == 403


def test_dashboard_admin_voit_resume(client, admin_headers):
    resp = client.get("/api/dashboard/summary", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "projets" in body
    assert "nb_projets" in body
    assert "avancement_moyen_pct" in body


def test_dashboard_ra_voit_resume(client):
    """Le RA a acces, et les chiffres totaux sont coherents avec la somme projets."""
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "ra-dash@test.fr",
            "password": "TestPass2026!",
            "full_name": "RA Dashboard",
            "role": "RA",
        },
    )
    token = resp.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    body = client.get("/api/dashboard/summary", headers=h).json()
    assert isinstance(body["projets"], list)
    # Totaux = sommes des projets
    assert body["nb_ecarts_ouverts_total"] == sum(
        p["nb_ecarts_ouverts"] for p in body["projets"]
    )


def test_dashboard_summary_par_projet(client, db, admin_headers):
    """Un projet avec saisies chantier doit afficher le bon avancement."""
    from app.models.caneco import CanecoExport, CanecoLine
    from app.models.field_entry import FieldEntry
    from app.models.project import Project

    p = Project(code="DASH-TST", name="Test dashboard", status="actif")
    db.add(p)
    db.commit()
    db.refresh(p)
    exp = CanecoExport(project_id=p.id, indice="A", file_name="x.xls", status="parsed")
    db.add(exp)
    db.commit()
    db.refresh(exp)

    # 4 circuits, 1 ligne tableau (ignore)
    lines = []
    for i, (style, cable) in enumerate(
        [("Tableau", None), ("Eclairage", "5G6"), ("PC", "3G2,5"), ("PC", "3G2,5"), ("PC", "3G2,5")]
    ):
        cl = CanecoLine(
            export_id=exp.id,
            row_index=i + 1,
            repere=f"R{i}",
            amont="TGBT",
            style=style,
            longueur=10.0,
            type_cable="U1000R2V",
            cable=cable,
            nb_cables_multi=1,
        )
        db.add(cl)
        lines.append(cl)
    db.commit()
    for cl in lines:
        db.refresh(cl)

    # Saisie sur 1 circuit / 4 -> avancement 25 %
    db.add(
        FieldEntry(
            caneco_line_id=lines[1].id,
            longueur_realisee=12.0,
            saisi_par=lines[0].id,  # any user id will do for unit test
            commentaire=None,
        )
    )
    db.commit()

    body = client.get("/api/dashboard/summary", headers=admin_headers).json()
    proj = next(x for x in body["projets"] if x["code"] == "DASH-TST")
    assert proj["nb_circuits"] == 4
    assert proj["nb_circuits_saisis"] == 1
    assert proj["avancement_pct"] == 25.0
    assert proj["longueur_prevue_m"] == 40.0  # 4 circuits x 10 m
    assert proj["longueur_realisee_m"] == 12.0
