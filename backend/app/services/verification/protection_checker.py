"""ProtectionChecker — verifie la coherence des protections CANECO.

Ecarts produits :
- E-004 : IB > In (protection sous-calibree)
- E-004 : IrTh × In < IB (reglage thermique insuffisant)
- E-011 : Icu < Icc presume (pouvoir de coupure insuffisant)

CORRECTION v1.2 : Icc dégressif par profondeur dans l'arborescence des tableaux.
L'utilisateur saisit le Icc presume a l'origine (TGBT) ; chaque etage aval applique
un facteur de decroissance (defaut 0.6). En bout de ligne, Icc baisse a quelques kA,
ce qui supprime les faux positifs E-011 sur les disjoncteurs divisionnaires.
"""

from __future__ import annotations

from app.models.caneco import CanecoLine
from app.services.verification.gap_emitter import A_CORRIGER, A_SIGNALER, BLOQUANT, GapEmitter

# Courant de court-circuit presume par defaut a l'origine (kA)
_DEFAULT_ICC_KA = 6.0

# Facteur de decroissance par etage dans l'arborescence des tableaux.
# Valeur empirique : a chaque saut amont->aval, Icc est multiplie par ce facteur.
# 0.6 correspond a une attenuation moyenne sur cable + jeu de barres + protection.
_DEFAULT_ICC_DECAY = 0.6

# Plancher : on ne descend pas en-dessous (au-dela : impedance dominante, Icc < 1 kA)
_MIN_ICC_FLOOR = 1.0

# Styles CANECO a ignorer (tableaux, jeux de barres, reserves, etc.)
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


def compute_depth_map(caneco_lines: list[CanecoLine]) -> dict[str, int]:
    """Calcule la profondeur de chaque ligne CANECO dans l'arborescence des tableaux.

    La profondeur est la longueur du chemin amont jusqu'a la racine (TGBT = 0).
    Detecte les cycles eventuels et limite la profondeur a 10.
    """
    by_repere: dict[str, CanecoLine] = {}
    for cl in caneco_lines:
        if cl.repere:
            by_repere[cl.repere.strip().upper()] = cl

    depth_cache: dict[str, int] = {}

    def _depth(repere: str, visited: set[str]) -> int:
        key = repere.strip().upper()
        if key in depth_cache:
            return depth_cache[key]
        if key in visited or len(visited) >= 10:
            depth_cache[key] = len(visited)
            return depth_cache[key]
        cl = by_repere.get(key)
        if cl is None or not cl.amont:
            depth_cache[key] = 0
            return 0
        amont_key = cl.amont.strip().upper()
        if amont_key == key or amont_key not in by_repere:
            depth_cache[key] = 0
            return 0
        d = 1 + _depth(amont_key, visited | {key})
        depth_cache[key] = d
        return d

    result: dict[str, int] = {}
    for cl in caneco_lines:
        if cl.id and cl.repere:
            result[cl.id] = _depth(cl.repere, set())
    return result


class ProtectionChecker:
    """Verifie les protections CANECO : calibrage, reglage et pouvoir de coupure."""

    def __init__(
        self,
        emitter: GapEmitter,
        icc_presumed_ka: float | None = None,
        depth_map: dict[str, int] | None = None,
        icc_decay: float = _DEFAULT_ICC_DECAY,
    ) -> None:
        self._emitter = emitter
        self._icc_origin = icc_presumed_ka if icc_presumed_ka is not None else _DEFAULT_ICC_KA
        self._depth_map = depth_map or {}
        self._decay = icc_decay

    def _icc_at(self, cl: CanecoLine) -> float:
        """Retourne le Icc estime au niveau de cette ligne."""
        depth = self._depth_map.get(cl.id, 0)
        icc = self._icc_origin * (self._decay ** depth)
        return max(icc, _MIN_ICC_FLOOR)

    def run(self, caneco_lines: list[CanecoLine]) -> None:
        """Parcourt les lignes CANECO et detecte les non-conformites de protection."""
        for cl in caneco_lines:
            if _is_tableau_style(cl.style):
                continue
            self._check_missing_data(cl)
            self._check_ib_vs_calibre(cl)
            self._check_icu(cl)

    # ------------------------------------------------------------------

    def _check_missing_data(self, cl: CanecoLine) -> None:
        """Signale les champs de protection nuls ou absents (oublis de calcul CANECO).

        Vise les departs ou la selection automatique n'a pas ete jouee : calibre, IB,
        ou regimes IrTh/IrMg manquants. Emet un E-019 par champ manquant.
        """
        repere = cl.repere or "—"
        missing: list[tuple[str, object]] = []
        if cl.calibre is None or cl.calibre == 0:
            missing.append(("calibre In", cl.calibre))
        if cl.ib is None or cl.ib == 0:
            missing.append(("courant d'emploi IB", cl.ib))

        for field_label, value in missing:
            self._emitter.emit(
                code="E-019",
                title=f"{field_label} manquant ou nul — depart non calcule dans CANECO",
                severity=A_SIGNALER,
                description=(
                    f"Circuit '{repere}' : {field_label} = "
                    f"{value if value is not None else 'non renseigne'}. "
                    f"Ce champ doit etre renseigne pour valider la coherence de la protection."
                ),
                caneco_line_id=cl.id,
                caneco_repere=cl.repere,
                caneco_amont=cl.amont,
                fields_compared={"champ_manquant": field_label, "valeur": value},
                suggested_action=(
                    "Verifier dans CANECO que le bilan de puissance et la selection du "
                    "disjoncteur ont bien ete executes pour ce depart."
                ),
                norm_rule_code="DATA-PROT",
            )

    # ------------------------------------------------------------------

    def _check_ib_vs_calibre(self, cl: CanecoLine) -> None:
        ib = cl.ib
        calibre = cl.calibre
        if ib is None or ib <= 0 or calibre is None or calibre <= 0:
            return

        repere = cl.repere or "—"

        if ib > calibre:
            self._emitter.emit(
                code="E-004",
                title="Protection sous-calibree : IB > In",
                severity=BLOQUANT,
                description=(
                    f"Circuit '{repere}' : courant d'emploi IB = {ib:.1f} A "
                    f"superieur au calibre de protection In = {calibre:.1f} A. "
                    f"La protection declenchera intempestivement en service normal."
                ),
                caneco_line_id=cl.id,
                caneco_repere=cl.repere,
                caneco_amont=cl.amont,
                fields_compared={"IB_A": ib, "In_A": calibre},
                suggested_action=(
                    f"Augmenter le calibre In a au moins {_next_standard_calibre(ib):.0f} A "
                    f"ou reduire la charge du circuit."
                ),
                norm_rule_code="NFC-008",
            )

        # Verifier le reglage thermique IrTh
        if cl.ir_th_in is not None and cl.ir_th_in > 0:
            ir_th_abs = cl.ir_th_in * calibre
            if ir_th_abs < ib:
                self._emitter.emit(
                    code="E-004",
                    title="Reglage thermique IrTh insuffisant : IrTh × In < IB",
                    severity=BLOQUANT,
                    description=(
                        f"Circuit '{repere}' : reglage IrTh = {cl.ir_th_in:.2f} "
                        f"x {calibre:.0f} A = {ir_th_abs:.1f} A "
                        f"inferieur a IB = {ib:.1f} A. "
                        f"Le disjoncteur ne protegera pas le circuit contre les surcharges."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    caneco_amont=cl.amont,
                    fields_compared={
                        "IrTh_ratio": cl.ir_th_in,
                        "IrTh_abs_A": round(ir_th_abs, 2),
                        "IB_A": ib,
                        "In_A": calibre,
                    },
                    suggested_action=(
                        f"Regler IrTh a au moins {ib / calibre:.2f} "
                        f"(soit {ib:.1f} A) pour proteger le circuit."
                    ),
                    norm_rule_code="NFC-021",
                )

    def _check_icu(self, cl: CanecoLine) -> None:
        """Verifie que Icu est renseigne dans CANECO.

        CORRECTION v1.3 : suppression de la comparaison Icu vs Icc presume.
        Chaque tableau a son propre Icc reel, non disponible dans l'export, donc la
        comparaison globale produit des faux positifs. A la place, on signale les Icu
        nuls ou non renseignes — symptome d'un departe non calcule dans CANECO.
        """
        icu = cl.icu
        repere = cl.repere or "—"

        if icu is None or icu <= 0:
            self._emitter.emit(
                code="E-019",
                title="Icu manquant ou nul — depart non calcule dans CANECO",
                severity=A_CORRIGER,
                description=(
                    f"Circuit '{repere}' : Icu = {icu if icu is not None else 'non renseigne'}. "
                    f"Un Icu nul ou absent indique generalement que le disjoncteur n'a pas ete "
                    f"calcule dans CANECO (selection automatique non effectuee ou departe en "
                    f"reserve)."
                ),
                caneco_line_id=cl.id,
                caneco_repere=cl.repere,
                caneco_amont=cl.amont,
                fields_compared={
                    "Icu_kA": icu,
                    "champ_manquant": "Icu",
                },
                suggested_action=(
                    "Ouvrir CANECO, lancer le calcul de selection du disjoncteur pour ce depart, "
                    "ou retirer la ligne si c'est une reserve non equipee."
                ),
                norm_rule_code="DATA-Icu",
            )


# ---------------------------------------------------------------------------
# Calibres normalises (serie IEC 60898)
# ---------------------------------------------------------------------------

_STD_CALIBRES = [1, 2, 3, 4, 6, 10, 13, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250]


def _next_standard_calibre(ib: float) -> float:
    """Retourne le prochain calibre normalise superieur ou egal a ib."""
    for c in _STD_CALIBRES:
        if c >= ib:
            return float(c)
    return float(_STD_CALIBRES[-1])
