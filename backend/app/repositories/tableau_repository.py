"""Acces donnees pour les tableaux electriques et leurs departs.

L'upsert est idempotent : un tableau est identifie par (projet, repere
normalise). On conserve le ``qr_token`` existant pour qu'une etiquette QR deja
imprimee reste valide apres une reimportation CANECO.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.tableau import Tableau
from app.services.tableau.builder import TableauDerive, normalize_repere


def list_for_project(db: Session, project_id: str) -> list[Tableau]:
    return (
        db.query(Tableau)
        .filter(Tableau.project_id == project_id)
        .order_by(Tableau.repere)
        .all()
    )


def get_by_id(db: Session, tableau_id: str) -> Tableau | None:
    return db.query(Tableau).filter(Tableau.id == tableau_id).first()


def get_by_token(db: Session, token: str) -> Tableau | None:
    """Recherche un tableau par son token QR (route publique, lecture seule)."""
    if not token:
        return None
    return db.query(Tableau).filter(Tableau.qr_token == token).first()


def upsert_from_derived(
    db: Session,
    project_id: str,
    derived: list[TableauDerive],
) -> list[Tableau]:
    """Cree ou met a jour les tableaux d'un projet a partir des tableaux derives.

    - Tableau persistant (meme repere normalise present dans le nouvel export) :
      on conserve son ``id`` et son ``qr_token`` (les etiquettes QR deja
      imprimees et posees sur ce tableau restent valides), on rafraichit la
      designation.
    - Tableau nouveau : creation avec un ``qr_token`` aleatoire (defaut modele).
    - Tableau absent du nouvel export : supprime (le jeu de tableaux reflete
      exactement le CANECO courant — corrige aussi d'eventuels faux tableaux).

    Le recapitulatif (fiche) n'est pas stocke : il est toujours derive en
    direct du dernier export CANECO (source de verite).

    Returns:
        La liste des tableaux correspondant aux tableaux derives, dans l'ordre.
    """
    existing = {
        normalize_repere(t.repere): t
        for t in db.query(Tableau).filter(Tableau.project_id == project_id).all()
    }
    nouvelles_cles = {d.cle for d in derived}

    # Suppression des tableaux qui ne sont plus dans l'export (ou faux tableaux)
    for cle, tab in list(existing.items()):
        if cle not in nouvelles_cles:
            db.delete(tab)
            del existing[cle]

    result: list[Tableau] = []
    for d in derived:
        tab = existing.get(d.cle)
        if tab is None:
            tab = Tableau(
                project_id=project_id,
                repere=d.repere,
                designation=d.designation,
            )
            db.add(tab)
            db.flush()
            existing[d.cle] = tab
        else:
            tab.repere = d.repere
            tab.designation = d.designation
        result.append(tab)

    db.commit()
    for tab in result:
        db.refresh(tab)
    return result
