"""LineMatcher — rapprochement CANECO <-> Bordereau.

Strategie :
- Tableaux CANECO (style contient 'tableau' ou designation entre parentheses dans bordereau)
  -> match par repere extrait de la designation bordereau ex. "(TES1)" -> "TES1"
- Circuits CANECO -> match bordereau cable par section + materiau
- Signale les circuits CANECO sans equivalent bordereau (E-001)
- Signale les articles bordereau cable/tableau sans equivalent CANECO (E-002, E-013)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models.bordereau import BordereauLine
from app.models.caneco import CanecoLine
from app.services.verification.cable_utils import (
    normalize_material,
    parse_bordereau_section,
    parse_caneco_cable,
)
from app.services.verification.gap_emitter import A_CORRIGER, A_SIGNALER, INFO, GapEmitter

# Regex extrayant un repere entre parentheses depuis la designation bordereau
_RE_REPERE = re.compile(r"\(([A-Z0-9_\-]{2,30})\)", re.IGNORECASE)

# Suffixe de sous-tableau (rang ou division) : "TGBTDIV005", "TES1SJB003", "TADMRRG02"
# Le bordereau facture le tableau parent ("TGBT") en un seul article. Les sous-tableaux
# CANECO ne doivent donc pas declencher d'E-013 si leur parent est apparie.
_RE_SUB_TABLEAU = re.compile(r"^(.+?)(DIV|SJB|RG)\d+$", re.IGNORECASE)


def _parse_simple_section(value: str | None) -> float | None:
    """Parse une section simple (colonne neutre ou pe) : "1x70", "70", "G70", etc.

    Retourne None si la valeur est vide ou non reconnaissable.
    """
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    # Tentative directe (ex. "70", "1.5")
    try:
        return float(s.replace(",", "."))
    except ValueError:
        pass
    # Pattern "1x70", "1x150", "Nx<section>"
    m = re.search(r"\d+\s*[xX]\s*(\d+(?:[.,]\d+)?)", s)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return None
    # Pattern "G70" ou "gG70"
    m = re.search(r"[Gg]+\s*(\d+(?:[.,]\d+)?)", s)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return None
    return None


def _extract_parent_tableau(repere: str) -> str | None:
    """Extrait le repere du tableau parent d'un sous-tableau.

    Exemples :
        TGBTDIV005   -> TGBT
        TES1DIV009   -> TES1
        TGBTSJB008   -> TGBT
        TADMRRG02    -> TADMR
        TGBT         -> None  (deja un parent)
        TE-AUX-PT    -> None  (pas de suffixe DIV/SJB/RG)
    """
    if not repere:
        return None
    m = _RE_SUB_TABLEAU.match(repere.strip())
    if m:
        return m.group(1)
    return None

# Styles CANECO qui correspondent a un tableau ou a une ligne hors-circuit
_TABLEAU_STYLES = {
    "tableau", "td", "tgbt", "tgt", "tds", "armoire", "coffret",
    "distribution", "bus", "jeu de barres", "jdb",
    "reserve", "réserve", "parafoudre", "paraf",
}


def _is_tableau_style(style: str | None) -> bool:
    if not style:
        return False
    sl = style.strip().lower()
    return any(k in sl for k in _TABLEAU_STYLES)


@dataclass
class MatchResult:
    caneco_line: CanecoLine
    bordereau_line: BordereauLine | None


@dataclass
class MatchReport:
    matched: list[MatchResult] = field(default_factory=list)
    unmatched_caneco: list[CanecoLine] = field(default_factory=list)
    unmatched_bordereau: list[BordereauLine] = field(default_factory=list)


class LineMatcher:
    """Rapproche les lignes CANECO aux lignes bordereau."""

    def __init__(
        self,
        caneco_lines: list[CanecoLine],
        bordereau_lines: list[BordereauLine],
        emitter: GapEmitter,
    ) -> None:
        self._caneco = caneco_lines
        self._bordereau = bordereau_lines
        self._emitter = emitter

    # ------------------------------------------------------------------

    def run(self) -> MatchReport:
        report = MatchReport()

        # Separe tableaux et circuits CANECO
        tableau_caneco = [l for l in self._caneco if _is_tableau_style(l.style)]
        circuit_caneco = [l for l in self._caneco if not _is_tableau_style(l.style)]

        # Separe tableaux et cables bordereau
        bd_tableaux = [
            l for l in self._bordereau if (l.detected_kind or "") in ("tableau",)
        ]
        bd_cables = [
            l for l in self._bordereau if (l.detected_kind or "") in ("cable",)
        ]

        matched_bd_ids: set[str] = set()
        # Reperes de tableaux parents deja apparies au bordereau : evite d'emettre E-013
        # pour chaque sous-tableau (TGBTDIV001..009 partagent le meme article 'TGBT' au bordereau).
        matched_parent_repres: set[str] = set()
        # Eviter de dupliquer un E-013 quand plusieurs sous-tableaux d'un meme parent non apparie existent
        emitted_parent_e013: set[str] = set()

        # --- Rapprochement tableaux ---
        for cl in tableau_caneco:
            repere = (cl.repere or "").strip().upper()
            parent = (_extract_parent_tableau(repere) or "").upper()

            # 1. Sous-tableau dont le parent est deja apparie : on l'associe et on saute
            if parent and parent in matched_parent_repres:
                report.matched.append(MatchResult(cl, None))
                continue

            # 2. Match direct sur le repere complet
            bd_match = self._find_tableau_in_bordereau(repere, bd_tableaux, matched_bd_ids)

            # 3. Fallback : match sur le repere du tableau parent (sous-tableau facture en bloc)
            if not bd_match and parent and parent != repere:
                bd_match = self._find_tableau_in_bordereau(parent, bd_tableaux, matched_bd_ids)

            if bd_match:
                matched_bd_ids.add(bd_match.id)
                if parent:
                    matched_parent_repres.add(parent)
                # Le repere lui-meme est aussi un parent valide pour ses propres sous-tableaux
                matched_parent_repres.add(repere)
                report.matched.append(MatchResult(cl, bd_match))
            else:
                # Pas de match. Si c'est un sous-tableau d'un parent non apparie,
                # on emet UN seul E-013 par parent (pas un par enfant).
                report.unmatched_caneco.append(cl)
                key_for_emit = parent if parent else repere
                if key_for_emit in emitted_parent_e013:
                    continue
                emitted_parent_e013.add(key_for_emit)
                self._emitter.emit(
                    code="E-013",
                    title="Tableau CANECO absent du bordereau",
                    severity=A_CORRIGER,
                    description=(
                        f"Le tableau '{key_for_emit}' est present dans l'export CANECO "
                        f"mais aucun article 'tableau' correspondant n'a ete trouve dans le bordereau."
                        + (f" (regroupe {repere} et ses sous-tableaux DIV/SJB/RG)"
                           if parent and parent != repere else "")
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    caneco_amont=cl.amont,
                    caneco_row=cl.excel_row_number,
                    suggested_action=(
                        "Verifier que le tableau est bien prevu au bordereau "
                        "ou qu'il ne s'agit pas d'un tableau de renvoi."
                    ),
                )

        # --- Rapprochement circuits par section + materiau ---
        # Construit un index bordereau : (section_mm2, materiau) -> list[BordereauLine]
        bd_index: dict[tuple[float, str], list[BordereauLine]] = {}
        for bl in bd_cables:
            sec = parse_bordereau_section(bl.detected_section_mm2)
            mat = normalize_material(bl.detected_material) or "Cu"
            if sec is not None:
                key = (sec, mat)
                bd_index.setdefault(key, []).append(bl)

        for cl in circuit_caneco:
            sec = parse_caneco_cable(cl.cable)
            mat = normalize_material(cl.ame) or "Cu"
            bd_match = None
            if sec is not None:
                key = (sec, mat)
                candidates = [b for b in bd_index.get(key, []) if b.id not in matched_bd_ids]
                if candidates:
                    bd_match = candidates[0]
                    matched_bd_ids.add(bd_match.id)

            report.matched.append(MatchResult(cl, bd_match))
            if bd_match is None:
                report.unmatched_caneco.append(cl)
                repere = cl.repere or "—"
                if sec is None:
                    # Section non parsable : signaler sans bloquer (format inconnu ou ligne vide)
                    self._emitter.emit(
                        code="E-001",
                        title="Circuit CANECO absent du bordereau (section non identifiee)",
                        severity=INFO,
                        description=(
                            f"Le circuit '{repere}' (designation cable : '{cl.cable or '—'}') "
                            f"n'a pas pu etre rapproche du bordereau car la section n'a pas ete "
                            f"reconnue dans la designation."
                        ),
                        caneco_line_id=cl.id,
                        caneco_repere=cl.repere,
                        caneco_amont=cl.amont,
                        caneco_row=cl.excel_row_number,
                        fields_compared={
                            "cable_caneco_brut": cl.cable,
                            "neutre_caneco_brut": cl.neutre,
                            "pe_caneco_brut": cl.pe,
                            "materiau": mat,
                        },
                        suggested_action=(
                            "Verifier manuellement si un article bordereau correspond "
                            f"a ce circuit (designation cable : '{cl.cable or '—'}')."
                        ),
                    )
                else:
                    self._emitter.emit(
                        code="E-001",
                        title="Circuit CANECO absent du bordereau",
                        severity=A_SIGNALER,
                        description=(
                            f"Le circuit '{repere}' (section {sec} mm², designation cable "
                            f"'{cl.cable or '—'}', {mat}) est dans CANECO mais n'a pas "
                            f"d'article cable correspondant dans le bordereau."
                        ),
                        caneco_line_id=cl.id,
                        caneco_repere=cl.repere,
                        caneco_amont=cl.amont,
                        caneco_row=cl.excel_row_number,
                        fields_compared={
                            "section_mm2": sec,
                            "cable_caneco_brut": cl.cable,
                            "neutre_caneco_brut": cl.neutre,
                            "pe_caneco_brut": cl.pe,
                            "materiau": mat,
                        },
                        suggested_action=(
                            "Verifier si un article de section equivalente existe "
                            "sous une autre designation dans le bordereau."
                        ),
                    )

        # --- Articles bordereau sans equivalent CANECO ---
        # Pour les tableaux : emission individuelle (chaque tableau bordereau est unique)
        for bl in bd_tableaux:
            if bl.id not in matched_bd_ids:
                report.unmatched_bordereau.append(bl)
                self._emitter.emit(
                    code="E-013",
                    title="Tableau bordereau absent de CANECO",
                    severity=A_SIGNALER,
                    description=(
                        f"L'article bordereau '{bl.num_prix}' ({bl.designation or ''}) "
                        f"n'a pas de correspondant dans l'export CANECO."
                    ),
                    bordereau_line_id=bl.id,
                    bordereau_num_prix=bl.num_prix,
                    bordereau_row=bl.excel_row_number,
                    suggested_action=(
                        "Verifier si la ligne bordereau correspond a un tableau non exporte "
                        "ou a un article commun."
                    ),
                )

        # Pour les cables : regroupement quantitatif par (section, materiau).
        # Les sous-prix bordereau (505.1, 505.2, ..., 505.32) sont souvent N variantes
        # du meme cable. On n'emet E-002 que si le surplus depasse 10 % du pool, et
        # un seul gap par groupe (au lieu d'un par article).
        unmatched_cables_by_key: dict[tuple[float, str], list[BordereauLine]] = {}
        for bl in bd_cables:
            if bl.id in matched_bd_ids:
                continue
            sec = parse_bordereau_section(bl.detected_section_mm2)
            mat = normalize_material(bl.detected_material) or "Cu"
            if sec is None:
                # Section illisible : emission individuelle classique
                report.unmatched_bordereau.append(bl)
                self._emitter.emit(
                    code="E-002",
                    title="Cable bordereau sans circuit CANECO associe",
                    severity=A_SIGNALER,
                    description=(
                        f"L'article bordereau '{bl.num_prix}' ({bl.designation or ''}) "
                        f"n'a pas de correspondant dans l'export CANECO."
                    ),
                    bordereau_line_id=bl.id,
                    bordereau_num_prix=bl.num_prix,
                    bordereau_row=bl.excel_row_number,
                    suggested_action=(
                        "Verifier si la ligne bordereau correspond a un circuit non exporte "
                        "ou a un article commun (fourreaux, tiges filetees, etc.)."
                    ),
                )
                continue
            unmatched_cables_by_key.setdefault((sec, mat), []).append(bl)

        for (sec, mat), pool in unmatched_cables_by_key.items():
            # Taille totale du pool bordereau = matched + unmatched pour cette cle
            total_bd = len(bd_index.get((sec, mat), []))
            surplus = len(pool)
            ratio = surplus / total_bd if total_bd > 0 else 1.0
            for bl in pool:
                report.unmatched_bordereau.append(bl)

            # Si surplus <= 10 % du pool : tolerance, on n'emet pas (probable difference
            # de granularite CANECO vs bordereau, pas un vrai ecart).
            if ratio <= 0.10:
                continue

            # Un seul gap consolide pour le groupe entier
            num_prix_list = sorted({bl.num_prix for bl in pool if bl.num_prix})
            head = pool[0]
            self._emitter.emit(
                code="E-002",
                title=f"{surplus} cables bordereau sans circuit CANECO associe (section {sec} mm² {mat})",
                severity=A_SIGNALER,
                description=(
                    f"{surplus} articles bordereau de section {sec} mm² ({mat}) n'ont pas "
                    f"de correspondant dans l'export CANECO sur un pool de {total_bd} "
                    f"({ratio * 100:.0f} %). Sous-prix concernes : "
                    f"{', '.join(num_prix_list[:10])}"
                    f"{' (...)' if len(num_prix_list) > 10 else ''}."
                ),
                bordereau_line_id=head.id,
                bordereau_num_prix=head.num_prix,
                bordereau_row=head.excel_row_number,
                fields_compared={
                    "section_mm2": sec,
                    "materiau": mat,
                    "surplus_articles": surplus,
                    "pool_total": total_bd,
                    "ratio_surplus": round(ratio, 2),
                    "sous_prix": num_prix_list,
                },
                suggested_action=(
                    "Verifier si ces articles correspondent a des circuits non exportes "
                    "(plans definitifs vs CANECO), des fourreaux/cheminements, ou un "
                    "surdimensionnement quantitatif a la phase chiffrage."
                ),
            )

        # --- Verification de couverture des sections phase / neutre / PE ---
        # Pour chaque section UNIQUE presente dans CANECO (sur les 3 colonnes cable / neutre /
        # pe), on verifie qu'au moins UN article bordereau existe avec cette section.
        # Sans comptage quantitatif : si CANECO utilise 5 fois du 1x300, il suffit d'un seul
        # article 300 mm² au bordereau pour considerer la section couverte (le metre lineaire
        # se chiffre par categorie, pas par instance). Evite les faux positifs.
        self._check_sections_coverage(self._caneco, bd_cables, report)

        return report

    # ------------------------------------------------------------------

    def _check_sections_coverage(
        self,
        caneco_lines: list["CanecoLine"],
        bd_cables: list[BordereauLine],
        report: "MatchReport",
    ) -> None:
        """Verifie l'existence d'AU MOINS UN article bordereau par section CANECO unique.

        Couvre les 3 colonnes CANECO : `cable` (phases), `neutre`, `pe`. Le bordereau ne
        listant que des sections en mm², on travaille sur l'ensemble des sections (mm²).
        Un seul gap par section manquante (dedoublonnage strict).
        """
        # Sections presentes au bordereau (peu importe le materiau pour cette couverture)
        bordereau_sections: set[float] = set()
        for bl in bd_cables:
            s = parse_bordereau_section(bl.detected_section_mm2)
            if s is not None:
                bordereau_sections.add(round(s, 1))

        # Collecte les sections CANECO par origine (phase / neutre / PE) avec un exemple de ligne
        caneco_sections: dict[tuple[float, str], "CanecoLine"] = {}
        for cl in caneco_lines:
            if _is_tableau_style(cl.style):
                continue
            # Phase via parse_caneco_cable
            phase = parse_caneco_cable(cl.cable)
            if phase is not None:
                key = (round(phase, 1), "phase")
                caneco_sections.setdefault(key, cl)
            # Neutre : ex. "1x70" ou "70"
            n_sec = _parse_simple_section(cl.neutre)
            if n_sec is not None:
                key = (round(n_sec, 1), "neutre")
                caneco_sections.setdefault(key, cl)
            # PE : ex. "1x70" ou "70" (ou parfois enrichi par parse_caneco_pe_section)
            pe_sec = _parse_simple_section(cl.pe)
            if pe_sec is None and phase is not None:
                # fallback via designation cable type "5G6" → PE = phase
                from app.services.verification.cable_utils import parse_caneco_pe_section
                pe_sec = parse_caneco_pe_section(cl.cable, phase)
            if pe_sec is not None:
                key = (round(pe_sec, 1), "pe")
                caneco_sections.setdefault(key, cl)

        # Pour chaque section manquante au bordereau, emet UN seul gap
        already_emitted: set[float] = set()
        for (sec, origine), example_cl in caneco_sections.items():
            if sec in bordereau_sections:
                continue
            if sec in already_emitted:
                # Une section donnee peut apparaitre sur phase + PE + neutre :
                # on emet un seul gap par section, pas un par origine.
                continue
            already_emitted.add(sec)
            self._emitter.emit(
                code="E-001",
                title=f"Section {sec} mm² presente dans CANECO mais absente du bordereau",
                severity=A_SIGNALER,
                description=(
                    f"La section {sec} mm² est utilisee dans CANECO (colonne {origine}, "
                    f"ex. circuit '{example_cl.repere or '—'}') mais aucun article cable "
                    f"de cette section n'a ete trouve dans le bordereau. La quantite n'est "
                    f"pas comparee — un seul article suffit a couvrir N occurrences CANECO."
                ),
                caneco_line_id=example_cl.id,
                caneco_repere=example_cl.repere,
                caneco_amont=example_cl.amont,
                caneco_row=example_cl.excel_row_number,
                fields_compared={
                    "section_mm2": sec,
                    "origine_caneco": origine,
                    "cable_caneco_brut": example_cl.cable,
                    "neutre_caneco_brut": example_cl.neutre,
                    "pe_caneco_brut": example_cl.pe,
                    "presente_dans_bordereau": False,
                    "sections_bordereau_disponibles": sorted(bordereau_sections),
                },
                suggested_action=(
                    f"Ajouter un article cable de section {sec} mm² au bordereau, ou "
                    f"verifier si CANECO utilise une section sur-dimensionnee a corriger."
                ),
            )

    # ------------------------------------------------------------------

    @staticmethod
    def _find_tableau_in_bordereau(
        repere: str,
        bd_tableaux: list[BordereauLine],
        already_matched: set[str],
    ) -> BordereauLine | None:
        """Cherche un article tableau dans le bordereau par repere."""
        for bl in bd_tableaux:
            if bl.id in already_matched:
                continue
            designation = (bl.designation or "").upper()
            # Cherche "(TES1)" ou "TES1" dans la designation
            m = _RE_REPERE.search(designation)
            if m and m.group(1).upper() == repere:
                return bl
            if repere and repere in designation:
                return bl
        return None
