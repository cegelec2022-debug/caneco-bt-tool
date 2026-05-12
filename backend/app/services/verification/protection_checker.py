"""ProtectionChecker — verifie la coherence des protections CANECO.

Ecarts produits :
- E-004 : IB > In (protection sous-calibree)
- E-004 : IrTh × In < IB (reglage thermique insuffisant)
- E-011 : Icu < Icc presume (pouvoir de coupure insuffisant)
"""

from __future__ import annotations

from app.models.caneco import CanecoLine
from app.services.verification.gap_emitter import BLOQUANT, GapEmitter

# Courant de court-circuit presume par defaut si non disponible (kA)
_DEFAULT_ICC_KA = 6.0


class ProtectionChecker:
    """Verifie les protections CANECO : calibrage, reglage et pouvoir de coupure."""

    def __init__(self, emitter: GapEmitter, icc_presumed_ka: float | None = None) -> None:
        self._emitter = emitter
        self._icc = icc_presumed_ka if icc_presumed_ka is not None else _DEFAULT_ICC_KA

    def run(self, caneco_lines: list[CanecoLine]) -> None:
        """Parcourt les lignes CANECO et detecte les non-conformites de protection."""
        for cl in caneco_lines:
            self._check_ib_vs_calibre(cl)
            self._check_icu(cl)

    # ------------------------------------------------------------------

    def _check_ib_vs_calibre(self, cl: CanecoLine) -> None:
        ib = cl.ib
        calibre = cl.calibre
        if ib is None or calibre is None or calibre <= 0:
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

        if icu < self._icc:
            self._emitter.emit(
                code="E-011",
                title="Pouvoir de coupure Icu insuffisant vs Icc presume",
                severity=BLOQUANT,
                description=(
                    f"Circuit '{repere}' : Icu = {icu:.1f} kA "
                    f"inferieur au Icc presume = {self._icc:.1f} kA. "
                    f"En cas de court-circuit, le disjoncteur risque d'exploser."
                ),
                caneco_line_id=cl.id,
                caneco_repere=cl.repere,
                fields_compared={
                    "Icu_kA": icu,
                    "Icc_presume_kA": self._icc,
                },
                suggested_action=(
                    f"Remplacer par un disjoncteur dont le Icu est "
                    f"superieur ou egal a {self._icc:.1f} kA."
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
