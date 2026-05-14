"""Carnet de cables — agregation des lignes CANECO par type et section.

Produit deux livrables pour le BE :
- Sommaire : ligne par (type_cable + section CANECO), avec longueur totale,
  nb circuits, nb occurrences, % du total projet.
- Rapport : KPIs synthetiques (longueur totale, top 5, sous-totaux par tableau aval).
"""

from app.services.cable_book.builder import (
    CableBookEntry,
    CableBookReport,
    build_cable_book,
    extract_cable_parameters,
    normalize_section_display,
)

__all__ = [
    "CableBookEntry",
    "CableBookReport",
    "build_cable_book",
    "extract_cable_parameters",
    "normalize_section_display",
]
