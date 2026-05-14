"""SuggestionEngine — heuristiques de bonnes pratiques (severite INFO).

Charge suggestions_rules.json et produit des gaps E-010 non bloquants.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.models.caneco import CanecoLine
from app.services.verification.cable_utils import (
    normalize_material,
    parse_caneco_cable,
    parse_caneco_conductors,
)
from app.services.verification.gap_emitter import INFO, GapEmitter
from app.services.verification.protection_checker import _next_standard_calibre

_RULES_PATH = Path(__file__).parent / "suggestions_rules.json"

# Section minimale normative par calibre (approximation conservative)
_MIN_SECTION_BY_CALIBRE: list[tuple[float, float]] = [
    (6, 1.5), (16, 1.5), (20, 2.5), (32, 4.0), (50, 6.0),
    (63, 10.0), (80, 16.0), (100, 25.0), (125, 35.0), (160, 50.0),
]


def _min_section_for_calibre(calibre_a: float) -> float:
    for cal_max, sec in _MIN_SECTION_BY_CALIBRE:
        if calibre_a <= cal_max:
            return sec
    return 95.0


def _load_rules() -> list[dict]:
    with open(_RULES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return [r for r in data["rules"] if r.get("enabled", True)]


def _style_matches(style: str | None, keywords: list[str]) -> bool:
    if not style:
        return False
    sl = style.lower()
    return any(k.lower() in sl for k in keywords)


class SuggestionEngine:
    """Produit des suggestions de bonnes pratiques (non bloquantes)."""

    def __init__(self, emitter: GapEmitter) -> None:
        self._emitter = emitter
        self._rules = _load_rules()

    def run(self, caneco_lines: list[CanecoLine]) -> None:
        for rule in self._rules:
            check_type = rule.get("check_type")
            if not check_type:
                continue
            handler = getattr(self, f"_sug_{check_type}", None)
            if handler:
                handler(rule, caneco_lines)

    # ------------------------------------------------------------------

    def _sug_oversized_section(self, rule: dict, lines: list[CanecoLine]) -> None:
        params = rule.get("parameters", {})
        ratio = params.get("ratio_threshold", 2.0)
        for cl in lines:
            if cl.calibre is None:
                continue
            sec = parse_caneco_cable(cl.cable)
            if sec is None:
                continue
            min_sec = _min_section_for_calibre(cl.calibre)
            if sec > min_sec * ratio:
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=rule["name"],
                    severity=INFO,
                    description=(
                        f"Circuit '{cl.repere or '—'}' : section {sec} mm² "
                        f"(designation brute '{cl.cable or '—'}') est "
                        f"{sec / min_sec:.1f}× la section minimale normative "
                        f"({min_sec} mm² pour {cl.calibre:.0f} A)."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    caneco_amont=cl.amont,
                    caneco_row=cl.excel_row_number,
                    fields_compared={
                        "section_mm2": sec,
                        "cable_caneco_brut": cl.cable,
                        "min_normative_mm2": min_sec,
                        "ratio": round(sec / min_sec, 2),
                    },
                    norm_rule_code=rule["id"],
                    suggested_action=(
                        "Verifier si la section est imposee par le CPS ou par une "
                        "contrainte de chute de tension, sinon envisager une reduction."
                    ),
                )

    def _sug_oversized_calibre(self, rule: dict, lines: list[CanecoLine]) -> None:
        params = rule.get("parameters", {})
        ratio = params.get("ratio_threshold", 2.0)
        for cl in lines:
            if cl.calibre is None or cl.ib is None or cl.ib <= 0:
                continue
            if cl.calibre > cl.ib * ratio:
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=rule["name"],
                    severity=INFO,
                    description=(
                        f"Circuit '{cl.repere or '—'}' : calibre {cl.calibre:.0f} A "
                        f"est {cl.calibre / cl.ib:.1f}× le courant d'emploi "
                        f"IB = {cl.ib:.1f} A."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    caneco_amont=cl.amont,
                    caneco_row=cl.excel_row_number,
                    fields_compared={
                        "calibre_A": cl.calibre,
                        "IB_A": cl.ib,
                        "ratio": round(cl.calibre / cl.ib, 2),
                    },
                    norm_rule_code=rule["id"],
                    suggested_action=(
                        "Verifier si le calibre peut etre optimise. "
                        "Un calibre reduit peut ameliorer la selectivite."
                    ),
                )

    def _sug_long_cable_recheck(self, rule: dict, lines: list[CanecoLine]) -> None:
        params = rule.get("parameters", {})
        threshold = params.get("length_threshold_m", 50.0)
        margin = params.get("suggested_margin_pct", 15.0)
        for cl in lines:
            if cl.longueur and cl.longueur >= threshold:
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=rule["name"],
                    severity=INFO,
                    description=(
                        f"Circuit '{cl.repere or '—'}' : longueur CANECO = {cl.longueur:.0f} m. "
                        f"Recalculer la chute de tension avec une longueur majoree de {margin:.0f} %."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    caneco_amont=cl.amont,
                    caneco_row=cl.excel_row_number,
                    fields_compared={
                        "longueur_m": cl.longueur,
                        "longueur_majoree_m": round(cl.longueur * (1 + margin / 100), 1),
                    },
                    norm_rule_code=rule["id"],
                    suggested_action=(
                        f"Recalculer dans CANECO avec une longueur de "
                        f"{cl.longueur * (1 + margin / 100):.0f} m (+ {margin:.0f} %)."
                    ),
                )

    def _sug_aluminium_conductor_warning(self, rule: dict, lines: list[CanecoLine]) -> None:
        params = rule.get("parameters", {})
        mat_kw = params.get("material_keyword", "Al")
        for cl in lines:
            mat = normalize_material(cl.ame)
            if mat == normalize_material(mat_kw):
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=rule["name"],
                    severity=INFO,
                    description=(
                        f"Circuit '{cl.repere or '—'}' utilise un conducteur aluminium. "
                        f"Verifier que les connexions sont compatibles."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    caneco_amont=cl.amont,
                    caneco_row=cl.excel_row_number,
                    norm_rule_code=rule["id"],
                    suggested_action=(
                        "Utiliser des bornes bimetalliques ou specifiques aluminium. "
                        "Prevoir une verification periodique du serrage des connexions."
                    ),
                )

    def _sug_missing_ddr_check(self, rule: dict, lines: list[CanecoLine]) -> None:
        for cl in lines:
            diff = (cl.bloc_differentiel or "").strip()
            if not diff:
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=rule["name"],
                    severity=INFO,
                    description=(
                        f"Circuit '{cl.repere or '—'}' : aucun differentiel renseigne dans CANECO. "
                        f"Verifier si une DDR est prevue en tete de tableau."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    caneco_amont=cl.amont,
                    caneco_row=cl.excel_row_number,
                    norm_rule_code=rule["id"],
                    suggested_action=(
                        "Verifier si ce circuit est couvert par une DDR de tete "
                        "ou s'il necessite sa propre protection differentielle."
                    ),
                )

    def _sug_curve_mismatch(self, rule: dict, lines: list[CanecoLine]) -> None:
        params = rule.get("parameters", {})
        preferred_map: dict[str, str] = params.get("preferred_curve_by_style", {})
        curve_ranges: dict[str, list[float]] = params.get("curve_ranges", {
            "B": [3.0, 5.0], "C": [5.0, 10.0], "D": [10.0, 20.0]
        })

        for cl in lines:
            ir_mg = cl.ir_mg_in
            if ir_mg is None:
                continue
            # Determine courbe actuelle
            current = None
            for curve, rng in curve_ranges.items():
                if rng[0] <= ir_mg <= rng[1]:
                    current = curve
                    break

            if current is None:
                continue

            # Cherche la courbe preferee pour ce style
            preferred = None
            style = (cl.style or "").lower()
            for kw, curve in preferred_map.items():
                if kw in style:
                    preferred = curve
                    break

            if preferred and current != preferred:
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=rule["name"],
                    severity=INFO,
                    description=(
                        f"Circuit '{cl.repere or '—'}' ({cl.style}) : "
                        f"courbe '{current}' (IrMg/IN = {ir_mg:.1f}) "
                        f"— courbe recommandee '{preferred}' pour ce type de charge."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    caneco_amont=cl.amont,
                    caneco_row=cl.excel_row_number,
                    fields_compared={
                        "courbe_actuelle": current,
                        "courbe_recommandee": preferred,
                        "IrMg_In": ir_mg,
                    },
                    norm_rule_code=rule["id"],
                    suggested_action=(
                        f"Envisager le passage a la courbe '{preferred}' "
                        f"apres validation avec le BET."
                    ),
                )

    def _sug_neutral_reduction_opportunity(self, rule: dict, lines: list[CanecoLine]) -> None:
        params = rule.get("parameters", {})
        min_sec = params.get("min_section_for_reduction_mm2", 16.0)
        styles = params.get("applicable_styles", [])
        for cl in lines:
            if styles and not _style_matches(cl.style, styles):
                continue
            nb = parse_caneco_conductors(cl.cable)
            if nb != 5:  # triphasé 5G -> neutre = phase
                continue
            sec = parse_caneco_cable(cl.cable)
            if sec is not None and sec > min_sec:
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=rule["name"],
                    severity=INFO,
                    description=(
                        f"Circuit triphasé '{cl.repere or '—'}' : cable 5G{sec:.0f} "
                        f"— neutre potentiellement reductible a {sec / 2:.0f} mm²."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    caneco_amont=cl.amont,
                    caneco_row=cl.excel_row_number,
                    norm_rule_code=rule["id"],
                    suggested_action=(
                        f"Pour les charges lineaires equilibrees, le neutre peut etre "
                        f"reduit a {sec / 2:.0f} mm² apres verification des harmoniques."
                    ),
                )

    # Suggestions non automatisables sans infos supplementaires
    def _sug_voltage_drop_near_limit(self, r: dict, l: list[CanecoLine]) -> None:
        pass

    def _sug_cable_type_overspec(self, r: dict, l: list[CanecoLine]) -> None:
        pass

    def _sug_missing_cable_tray_in_bordereau(self, r: dict, l: list[CanecoLine]) -> None:
        pass

    def _sug_ddr_type_mismatch(self, r: dict, l: list[CanecoLine]) -> None:
        pass

    def _sug_surge_protection_recommendation(self, r: dict, l: list[CanecoLine]) -> None:
        pass

    def _sug_oversized_pe(self, r: dict, l: list[CanecoLine]) -> None:
        pass

    def _sug_curve_heterogeneity(self, r: dict, l: list[CanecoLine]) -> None:
        pass

    def _sug_partial_selectivity_warning(self, r: dict, l: list[CanecoLine]) -> None:
        pass
