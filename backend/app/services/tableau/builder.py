"""Derivation des tableaux electriques depuis un export CANECO.

Regle metier (generique, valable pour tous les projets) :

- Un *tableau* electrique est une ligne CANECO dont la colonne ``style`` est
  un type de jeu de barres / armoire (``Tableau``, ``Armoire``, ``Coffret``).
  Le repere de cette ligne EST le repere du tableau (TGBT, TES1, TGADM...).
- Les autres lignes (``Eclairage``, ``PC``, ``GRILLE``, ``RES_EQUIP``...) sont
  des *circuits* (departs), pas des tableaux. Un circuit comme ``1E/TES1`` ne
  doit jamais apparaitre comme un tableau.
- Les exports CANECO contiennent souvent chaque ligne en double : on
  dedoublonne sur une signature stable avant tout traitement.

La fiche d'un tableau = les caracteristiques de SA propre ligne CANECO,
presentees verticalement et regroupees par theme (identification, puissance,
cable d'alimentation, protection) — c'est la fiche client.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from app.models.caneco import CanecoLine

# Mots-cles identifiant une ligne "tableau" via la colonne style (generique).
_BOARD_KEYWORDS = ("tableau", "armoire", "coffret")


def normalize_repere(repere: str | None) -> str:
    """Cle de dedoublonnage d'un repere (insensible casse / espaces)."""
    return (repere or "").strip().upper()


def is_tableau_style(style: str | None) -> bool:
    """Vrai si le style CANECO designe un tableau / armoire / coffret."""
    s = (style or "").strip().lower()
    return any(k in s for k in _BOARD_KEYWORDS)


def _fmt_num(value: float | int | None, unit: str = "", decimals: int = 2) -> str | None:
    """Formate un nombre a la francaise (virgule), avec unite optionnelle."""
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int):
        txt = str(value)
    else:
        txt = f"{value:.{decimals}f}".replace(".", ",")
    return f"{txt} {unit}".strip()


def _txt(value: str | None) -> str | None:
    v = (value or "").strip()
    return v or None


# Sections de la fiche client : (titre, [(libelle, valeur_brute_callable)])
# L'ordre et le regroupement sont volontairement plus structures que l'exemple
# fourni, pour un rendu professionnel.
def _build_sections(cl: CanecoLine) -> list[dict]:
    return [
        {
            "title": "Identification",
            "rows": [
                {"label": "Repere", "value": _txt(cl.repere)},
                {"label": "Designation", "value": _txt(cl.designation)},
                {"label": "Alimente depuis (amont)", "value": _txt(cl.amont)},
                {"label": "Style", "value": _txt(cl.style)},
            ],
        },
        {
            "title": "Puissance",
            "rows": [
                {"label": "Nb recepteurs", "value": _fmt_num(cl.nb_recepteurs)},
                {"label": "Consommation", "value": _txt(cl.consommation)},
                {"label": "Courant d'emploi IB", "value": _fmt_num(cl.ib, "A")},
            ],
        },
        {
            "title": "Cable d'alimentation",
            "rows": [
                {"label": "Type de cable", "value": _txt(cl.type_cable)},
                {"label": "Cable", "value": _txt(cl.cable)},
                {"label": "Nb cables en parallele", "value": _fmt_num(cl.nb_cables_multi)},
                {"label": "Ame", "value": _txt(cl.ame)},
                {"label": "Neutre", "value": _txt(cl.neutre)},
                {"label": "PE ou PEN", "value": _txt(cl.pe)},
                {"label": "Longueur", "value": _fmt_num(cl.longueur, "m")},
            ],
        },
        {
            "title": "Protection",
            "rows": [
                {"label": "Calibre", "value": _fmt_num(cl.calibre, "A")},
                {"label": "Bloc de coupure", "value": _txt(cl.bloc_coupure)},
                {"label": "Bloc declencheur", "value": _txt(cl.bloc_declencheur)},
                {"label": "Bloc differentiel", "value": _txt(cl.bloc_differentiel)},
                {"label": "Pouvoir de coupure Icu", "value": _fmt_num(cl.icu, "kA")},
                {"label": "IrTh / IN", "value": _fmt_num(cl.ir_th_in)},
                {"label": "IrMg / IN", "value": _fmt_num(cl.ir_mg_in)},
            ],
        },
    ]


@dataclass
class TableauDerive:
    """Un tableau electrique (une ligne CANECO de style tableau) + son contexte."""

    repere: str
    designation: str | None
    sections: list[dict] = field(default_factory=list)
    nb_departs: int = 0
    longueur_totale_m: float = 0.0

    @property
    def cle(self) -> str:
        return normalize_repere(self.repere)


def _dedupe(lines: Iterable[CanecoLine]) -> list[CanecoLine]:
    """Supprime les doublons exacts (les exports CANECO doublent les lignes)."""
    seen: set[tuple] = set()
    out: list[CanecoLine] = []
    for cl in lines:
        sig = (
            normalize_repere(cl.repere),
            normalize_repere(cl.amont),
            (cl.style or "").strip().lower(),
            (cl.cable or "").strip(),
            cl.longueur,
            (cl.consommation or "").strip(),
        )
        if sig in seen:
            continue
        seen.add(sig)
        out.append(cl)
    return out


def derive_tableaux(caneco_lines: Iterable[CanecoLine]) -> list[TableauDerive]:
    """Derive la liste des tableaux electriques d'un export CANECO.

    Args:
        caneco_lines: Lignes CANECO d'un export.

    Returns:
        Liste de TableauDerive (un par tableau reel, dedoublonne par repere),
        triee par repere. Chaque tableau porte sa fiche (sections) et le
        nombre / la longueur des circuits qu'il alimente.
    """
    lines = _dedupe(caneco_lines)

    tableau_lines = [cl for cl in lines if is_tableau_style(cl.style)]
    circuits = [cl for cl in lines if not is_tableau_style(cl.style)]

    # Circuits regroupes par tableau amont (pour le compte de departs / longueur)
    departs_par_cle: dict[str, list[CanecoLine]] = {}
    for c in circuits:
        cle = normalize_repere(c.amont)
        if cle:
            departs_par_cle.setdefault(cle, []).append(c)

    # Import local pour eviter une dependance circulaire avec cable_book.
    from app.services.cable_book.builder import _contributions_for_line

    def _longueur_caneco(deps: list[CanecoLine]) -> float:
        """Somme methode CANECO (decomposition conducteurs + paralleles + N + PE)."""
        return round(
            sum(c.longueur for d in deps for c in _contributions_for_line(d)),
            2,
        )

    tableaux: dict[str, TableauDerive] = {}
    for cl in tableau_lines:
        cle = normalize_repere(cl.repere)
        if not cle or cle in tableaux:
            continue  # premier representant du tableau (dedoublonnage par repere)
        deps = departs_par_cle.get(cle, [])
        tableaux[cle] = TableauDerive(
            repere=(cl.repere or "").strip(),
            designation=_txt(cl.designation),
            sections=_build_sections(cl),
            nb_departs=len(deps),
            longueur_totale_m=_longueur_caneco(deps),
        )

    return sorted(tableaux.values(), key=lambda t: t.repere.upper())
