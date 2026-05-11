"""Tests du stock de cables et regles metier de saisie chantier."""

from __future__ import annotations

import pytest


@pytest.fixture
def project_with_lines(db, admin_token):
    """Cree un projet + export + 2 lignes CANECO :
    - L1 : 100 m de 5G6 (Cuivre)
    - L2 : 200 m de 3X(1x150) Alu (= 3 conducteurs unipolaires 150 mm²)
    """
    from app.models.caneco import CanecoExport, CanecoLine
    from app.models.project import Project

    p = Project(code="STK-TST", name="Test stock", status="actif")
    db.add(p)
    db.commit()
    db.refresh(p)

    exp = CanecoExport(
        project_id=p.id, indice="A", file_name="x.xls", status="parsed", line_count=2
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)

    l1 = CanecoLine(
        export_id=exp.id,
        row_index=1,
        repere="C1",
        amont="TGBT",
        style="Eclairage",
        longueur=100.0,
        type_cable="U1000R2V",
        cable="5G6",
        ame="1",
        nb_cables_multi=1,
    )
    l2 = CanecoLine(
        export_id=exp.id,
        row_index=2,
        repere="C2",
        amont="TGBT",
        style="PC",
        longueur=200.0,
        type_cable="U1000AR2V",
        cable="3X(1x150)",
        ame="2",
        nb_cables_multi=1,
    )
    db.add_all([l1, l2])
    db.commit()
    db.refresh(l1)
    db.refresh(l2)
    return p.id, l1.id, l2.id


# --- Saisie chantier : commentaire obligatoire -----------------------------


def test_saisie_zero_exige_commentaire(client, admin_headers, project_with_lines):
    pid, l1, _ = project_with_lines
    resp = client.put(
        f"/api/projects/{pid}/field-entries/{l1}",
        json={"longueur_realisee": 0},
        headers=admin_headers,
    )
    assert resp.status_code == 422
    assert "commentaire" in resp.json()["detail"].lower()


def test_saisie_zero_avec_commentaire_passe(
    client, admin_headers, project_with_lines
):
    pid, l1, _ = project_with_lines
    resp = client.put(
        f"/api/projects/{pid}/field-entries/{l1}",
        json={"longueur_realisee": 0, "commentaire": "Circuit annule par BE"},
        headers=admin_headers,
    )
    assert resp.status_code == 200


def test_saisie_ecart_superieur_50_pct_exige_commentaire(
    client, admin_headers, project_with_lines
):
    """100 m prevu, 160 m reel = +60 % d'ecart."""
    pid, l1, _ = project_with_lines
    resp = client.put(
        f"/api/projects/{pid}/field-entries/{l1}",
        json={"longueur_realisee": 160},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_saisie_ecart_modere_passe_sans_commentaire(
    client, admin_headers, project_with_lines
):
    """100 m prevu, 130 m reel = +30 % : autorise sans commentaire."""
    pid, l1, _ = project_with_lines
    resp = client.put(
        f"/api/projects/{pid}/field-entries/{l1}",
        json={"longueur_realisee": 130},
        headers=admin_headers,
    )
    assert resp.status_code == 200


# --- Stock cables ----------------------------------------------------------


def test_stock_initial_vide(client, admin_headers, project_with_lines):
    pid, _, _ = project_with_lines
    resp = client.get(f"/api/projects/{pid}/cable-stock", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["nb_references"] == 0


def test_stock_se_remplit_auto_depuis_saisies(
    client, admin_headers, project_with_lines
):
    """Apres une saisie chantier, la reference correspondante apparait dans le stock."""
    pid, l1, _ = project_with_lines
    client.put(
        f"/api/projects/{pid}/field-entries/{l1}",
        json={"longueur_realisee": 95.0},
        headers=admin_headers,
    )
    body = client.get(
        f"/api/projects/{pid}/cable-stock", headers=admin_headers
    ).json()
    assert body["nb_references"] == 1
    ref = body["items"][0]
    assert ref["type_cable"] == "U1000R2V"
    assert ref["section_label"] == "5G6"
    assert ref["ame"] == "Cuivre"
    assert ref["quantite_utilisee"] == 95.0


def test_stock_unipolaire_ventile_par_section(
    client, admin_headers, project_with_lines
):
    """Une saisie sur 3X(1x150) (200 m prevus) ventile 200 m * 3 = 600 m
    sur la reference 1*150 mm² Alu si on remonte exactement la longueur prevue.
    Avec 100 m reels = 300 m unipolaires comptabilises."""
    pid, _, l2 = project_with_lines
    client.put(
        f"/api/projects/{pid}/field-entries/{l2}",
        json={"longueur_realisee": 100.0, "commentaire": "Pose partielle"},
        headers=admin_headers,
    )
    body = client.get(
        f"/api/projects/{pid}/cable-stock", headers=admin_headers
    ).json()
    ref = next(it for it in body["items"] if it["section_label"] == "1*150 mm²")
    assert ref["quantite_utilisee"] == 300.0
    assert ref["ame"] == "Alu"


def test_stock_upsert_quantites_et_alerte(
    client, admin_headers, project_with_lines
):
    """RA renseigne achete=500 livre=200 seuil=80 ; utilise auto via saisies."""
    pid, l1, _ = project_with_lines
    # saisie : 150 m reels sur 5G6
    client.put(
        f"/api/projects/{pid}/field-entries/{l1}",
        json={"longueur_realisee": 130.0},  # ecart 30% : pas de commentaire requis
        headers=admin_headers,
    )
    # RA met a jour le stock
    resp = client.put(
        f"/api/projects/{pid}/cable-stock",
        json={
            "type_cable": "U1000R2V",
            "section_label": "5G6",
            "ame": "Cuivre",
            "quantite_achetee": 500.0,
            "quantite_livree": 200.0,
            "seuil_alerte_min_m": 100.0,  # alerte si reste < 100 m
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    ref = next(
        it
        for it in resp.json()["items"]
        if it["type_cable"] == "U1000R2V" and it["section_label"] == "5G6"
    )
    assert ref["quantite_achetee"] == 500.0
    assert ref["quantite_livree"] == 200.0
    assert ref["quantite_utilisee"] == 130.0
    assert ref["stock_restant"] == 70.0  # 200 - 130
    assert ref["en_alerte"] is True  # 70 < 80 (seuil)


def test_stock_pas_d_alerte_si_seuil_zero(
    client, admin_headers, project_with_lines
):
    pid, l1, _ = project_with_lines
    client.put(
        f"/api/projects/{pid}/field-entries/{l1}",
        json={"longueur_realisee": 100.0},
        headers=admin_headers,
    )
    resp = client.put(
        f"/api/projects/{pid}/cable-stock",
        json={
            "type_cable": "U1000R2V",
            "section_label": "5G6",
            "ame": "Cuivre",
            "quantite_livree": 100.0,
        },
        headers=admin_headers,
    ).json()
    ref = next(it for it in resp["items"] if it["section_label"] == "5G6")
    assert ref["seuil_alerte_min_m"] == 0.0
    assert ref["en_alerte"] is False  # seuil 0 => jamais en alerte
