"""Tests de la route publique de fiche tableau (securite, lecture seule)."""

from __future__ import annotations


def test_token_inconnu_renvoie_404_generique(client):
    resp = client.get("/api/t/un-token-qui-nexiste-pas")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Fiche introuvable."


def test_route_publique_ne_demande_pas_d_authentification(client):
    # Aucune en-tete Authorization : on doit obtenir 404 (et non 401/403),
    # ce qui prouve que la route est bien publique et atteignable.
    resp = client.get("/api/t/inexistant")
    assert resp.status_code == 404


def test_fiche_pdf_token_inconnu_404(client):
    resp = client.get("/api/t/inexistant/fiche.pdf")
    assert resp.status_code == 404
