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
from app.services.verification.gap_emitter import BLOQUANT, GapEmitter

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
            self._check_ib_vs_calibre(cl)
            self._check_icu(cl)

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
        icu = cl.icu
        if icu is None:
            return

        repere = cl.repere or "—"
        icc_local = self._icc_at(cl)
        depth = self._depth_map.get(cl.id, 0)

        if icu < icc_local:
            self._emitter.emit(
                code="E-011",
                title="Pouvoir de coupure Icu insuffisant vs Icc presume",
                severity=BLOQUANT,
                description=(
                    f"Circuit '{repere}' (profondeur {depth} dans l'arborescence) : "
                    f"Icu = {icu:.1f} kA inferieur au Icc estime a ce niveau "
                    f"= {icc_local:.1f} kA (Icc origine {self._icc_origin:.1f} kA, "
                    f"facteur {self._decay} par etage). "
                    f"En cas de court-circuit, le disjoncteur risque d'exploser."
                ),
                caneco_line_id=cl.id,
                caneco_repere=cl.repere,
                fields_compared={
                    "Icu_kA": icu,
                    "Icc_local_kA": round(icc_local, 2),
                    "Icc_origine_kA": self._icc_origin,
                    "profondeur": depth,
                    "facteur_decroissance": self._decay,
                },
                suggested_action=(
                    f"Remplacer par un disjoncteur dont le Icu est "
                    f"superieur ou egal a {icc_local:.1f} kA, ou ajuster le Icc d'origine "
                    f"si la valeur saisie est trop conservative."
                ),
                norm_rule_code="NFC-011",
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
