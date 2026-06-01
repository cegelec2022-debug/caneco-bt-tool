"""Suivi du stock de cables — references + quantite utilisee auto-calculee.

La quantite utilisee d'une reference (type_cable, section_label, ame) est la
somme des longueurs reellement tirees sur les circuits de ce type. La regle
de decomposition est la meme que celle du carnet de cables (methode CANECO
BT) : on reutilise ``contributions_for_line`` pour ventiler chaque saisie
chantier sur les bonnes references.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models.cable_stock import CableStockItem
from app.models.caneco import CanecoLine
from app.models.field_entry import FieldEntry
from app.services.cable_book.builder import _contributions_for_line, build_cable_book


StockKey = tuple[str, str, str]  # (type_cable, section_label, ame)


@dataclass
class StockComputed:
    type_cable: str
    section_label: str
    ame: str
    section_mm2: float | None
    quantite_achetee: float
    quantite_livree: float
    quantite_utilisee: float
    seuil_alerte_min_m: float
    item_id: str | None = None  # None si la reference n'a pas encore d'enregistrement
    date_achat: date | None = None
    date_livraison_prevue: date | None = None

    @property
    def stock_restant(self) -> float:
        return round(self.quantite_livree - self.quantite_utilisee, 2)

    @property
    def en_alerte(self) -> bool:
        """Reste de stock sous le seuil minimum configure."""
        return (
            self.seuil_alerte_min_m > 0
            and self.stock_restant < self.seuil_alerte_min_m
        )


def _contributions_with_real_length(
    line: CanecoLine, real_length: float
) -> list[tuple[StockKey, float, float | None]]:
    """Ventile une saisie chantier sur les references stock.

    On reutilise ``_contributions_for_line`` puis on remplace la longueur
    unitaire prevue par la longueur reelle saisie, en proportion. Ainsi
    chaque conducteur unipolaire (phase, neutre, PE) recoit sa part en
    metres reellement tires.
    """
    base_contribs = _contributions_for_line(line)
    prevue = float(line.longueur or 0.0)
    if not base_contribs or prevue <= 0:
        # Cas degenere : pas de cable ou longueur prevue nulle ; on impute la
        # totalite a la premiere contribution (ou rien si aucune).
        if base_contribs:
            c = base_contribs[0]
            return [((c.type_cable, c.section_label, c.ame), real_length, c.section_mm2)]
        return []

    out: list[tuple[StockKey, float, float | None]] = []
    for c in base_contribs:
        # ratio = facteur de multiplication applique par contribution
        ratio = c.longueur / prevue if prevue > 0 else 0
        out.append(
            (
                (c.type_cable, c.section_label, c.ame),
                real_length * ratio,
                c.section_mm2,
            )
        )
    return out


def compute_usage(
    caneco_lines: list[CanecoLine],
    field_entries: list[FieldEntry],
) -> dict[StockKey, tuple[float, float | None]]:
    """Calcule la quantite utilisee + section associee pour chaque reference.

    Returns:
        Dict {(type, section, ame): (longueur_utilisee_m, section_mm2)}.
    """
    by_id: dict[str, CanecoLine] = {cl.id: cl for cl in caneco_lines}
    used: dict[StockKey, float] = defaultdict(float)
    sections: dict[StockKey, float | None] = {}

    for entry in field_entries:
        line = by_id.get(entry.caneco_line_id)
        if line is None:
            continue
        for key, length, sec in _contributions_with_real_length(
            line, entry.longueur_realisee
        ):
            used[key] += length
            sections.setdefault(key, sec)

    return {k: (round(v, 2), sections.get(k)) for k, v in used.items()}


def list_stock(
    db: Session,
    project_id: str,
    caneco_lines: list[CanecoLine],
    field_entries: list[FieldEntry],
) -> list[StockComputed]:
    """Combine les references stock du projet avec la consommation calculee.

    Les references stock peuvent etre :
    - enregistrees dans cable_stock_items (le RA / Chef y a renseigne des
      quantites ou un seuil) ;
    - implicitement detectees depuis les saisies chantier (utilisees mais pas
      encore declarees en stock — on les affiche quand meme pour que le Chef
      puisse les initialiser).
    """
    items = (
        db.query(CableStockItem)
        .filter(CableStockItem.project_id == project_id)
        .all()
    )
    by_key: dict[StockKey, CableStockItem] = {
        (it.type_cable, it.section_label, it.ame): it for it in items
    }
    usage = compute_usage(caneco_lines, field_entries)

    # Toutes les references presentes dans le CANECO (meme sans saisie chantier
    # et meme sans enregistrement stock). Permet au Chef de voir d'emblee la
    # liste complete des cables a tirer et de planifier ses livraisons.
    carnet_keys: dict[StockKey, float | None] = {}
    if caneco_lines:
        report = build_cable_book(caneco_lines)
        for entry in report.entries:
            carnet_keys[
                (entry.type_cable, entry.cable_caneco, entry.ame or "")
            ] = entry.section_mm2

    all_keys: set[StockKey] = set(by_key) | set(usage) | set(carnet_keys)

    result: list[StockComputed] = []
    for key in all_keys:
        type_cable, section_label, ame = key
        it = by_key.get(key)
        used_m, used_sec = usage.get(key, (0.0, None))
        section_mm2 = (
            (it.section_mm2 if it else None)
            or used_sec
            or carnet_keys.get(key)
        )
        result.append(
            StockComputed(
                type_cable=type_cable,
                section_label=section_label,
                ame=ame,
                section_mm2=section_mm2,
                quantite_achetee=it.quantite_achetee if it else 0.0,
                quantite_livree=it.quantite_livree if it else 0.0,
                quantite_utilisee=used_m,
                seuil_alerte_min_m=it.seuil_alerte_min_m if it else 0.0,
                item_id=it.id if it else None,
                date_achat=it.date_achat if it else None,
                date_livraison_prevue=it.date_livraison_prevue if it else None,
            )
        )

    # Tri : par type puis par section croissante (mise en mm²)
    result.sort(
        key=lambda s: (
            s.type_cable,
            s.section_mm2 if s.section_mm2 is not None else 0.0,
            s.section_label,
            s.ame,
        )
    )
    return result
