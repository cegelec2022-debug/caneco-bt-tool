"""NormChecker — applique les regles NF C 15-100 chargees depuis nfc15100_rules.json.

Ecarts produits : E-004, E-007, E-008, E-009, E-010, E-011, E-012, E-015, E-016, E-017, E-018.

Corrections v1.1 :
- NFC-012 (DDR prises habitation) : desormais A_SIGNALER avec mention contexte habitation
- E-009 chute de tension : A_SIGNALER (non BLOQUANT), seuil longueur 50 m
- Courbe B/C/D : garde contre IrMg/IN > 20 (valeur hors plage normative)
"""

from __future__ import annotations

import json
from pathlib import Path

from app.models.caneco import CanecoLine
from app.services.verification.cable_utils import (
    classify_tripping_curve,
    min_pe_section,
    normalize_material,
    parse_caneco_cable,
    parse_caneco_conductors,
    parse_caneco_pe_section,
)
from app.services.verification.gap_emitter import (
    A_CORRIGER,
    A_SIGNALER,
    BLOQUANT,
    INFO,
    GapEmitter,
)

_RULES_PATH = Path(__file__).parent / "nfc15100_rules.json"

_SEVERITY_MAP = {
    "BLOQUANT": BLOQUANT,
    "A_CORRIGER": A_CORRIGER,
    "A_SIGNALER": A_SIGNALER,
    "INFORMATION": INFO,
    "INFO": INFO,
}

# Styles CANECO qui representent un tableau ou jeu de barres (pas un depart cable)
_TABLEAU_STYLE_KW = {
    "tableau", "td", "tgbt", "tgt", "tds", "armoire", "coffret",
    "distribution", "bus", "jeu de barres", "jdb", "jeu", "jeux",
    "reserve", "réserve", "parafoudre", "paraf", "alimentation",
}

# Longueur minimale pour emettre un signal chute de tension
_LONGUEUR_THRESHOLD_DT = 50.0

# Valeur IrMg/IN maximale acceptable (au-dela : donnee suspecte, pas de classification courbe)
_IRMG_MAX = 20.0


def _load_rules() -> list[dict]:
    with open(_RULES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return [r for r in data["rules"] if r.get("enabled", True)]


def _style_matches(style: str | None, keywords: list[str]) -> bool:
    if not style:
        return False
    sl = style.lower()
    return any(k.lower() in sl for k in keywords)


def _is_tableau_line(cl: CanecoLine) -> bool:
    """Retourne True si la ligne CANECO est un tableau / jeu de barres."""
    style = (cl.style or "").lower()
    return any(k in style for k in _TABLEAU_STYLE_KW)


class NormChecker:
    """Applique les regles normatives NF C 15-100 aux lignes CANECO."""

    def __init__(self, emitter: GapEmitter) -> None:
        self._emitter = emitter
        self._rules = _load_rules()

    def run(self, caneco_lines: list[CanecoLine]) -> None:
        for rule in self._rules:
            check_type = rule.get("check_type")
            if not check_type:
                continue
            handler = getattr(self, f"_check_{check_type}", None)
            if handler:
                handler(rule, caneco_lines)

    # ------------------------------------------------------------------
    # Handlers de verifications
    # ------------------------------------------------------------------

    def _check_min_section_by_style(self, rule: dict, lines: list[CanecoLine]) -> None:
        params = rule.get("parameters", {})
        keywords = params.get("style_keywords", [])
        min_sec = params.get("min_section_mm2")
        if not keywords or min_sec is None:
            return

        for cl in lines:
            if _is_tableau_line(cl):
                continue
            if not _style_matches(cl.style, keywords):
                continue
            sec = parse_caneco_cable(cl.cable)
            mat = normalize_material(cl.ame) or "Cu"
            req_mat = params.get("material", "Cu")
            if mat != req_mat:
                continue
            if sec is not None and sec < min_sec:
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=rule["name"],
                    severity=_SEVERITY_MAP.get(rule["severity"], BLOQUANT),
                    description=(
                        f"Circuit '{cl.repere or '—'}' (style '{cl.style}') : "
                        f"section {sec} mm² < minimum NF C 15-100 {min_sec} mm²."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    fields_compared={
                        "section_mm2": sec,
                        "min_norme_mm2": min_sec,
                        "style": cl.style,
                    },
                    norm_rule_code=rule["id"],
                    suggested_action=(
                        f"Augmenter la section a au moins {min_sec} mm² "
                        f"conformement a {rule.get('source', 'NF C 15-100')}."
                    ),
                )

    def _check_min_section_by_calibre(self, rule: dict, lines: list[CanecoLine]) -> None:
        params = rule.get("parameters", {})
        keywords = params.get("style_keywords", [])
        min_sec = params.get("min_section_mm2")
        cal_max = params.get("calibre_max_a")
        cal_min = params.get("calibre_min_a", 0)
        if not keywords or min_sec is None or cal_max is None:
            return

        for cl in lines:
            if _is_tableau_line(cl):
                continue
            if not _style_matches(cl.style, keywords):
                continue
            if cl.calibre is None:
                continue
            if not (cal_min < cl.calibre <= cal_max):
                continue
            sec = parse_caneco_cable(cl.cable)
            if sec is not None and sec < min_sec:
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=rule["name"],
                    severity=_SEVERITY_MAP.get(rule["severity"], BLOQUANT),
                    description=(
                        f"Circuit '{cl.repere or '—'}' (calibre {cl.calibre} A) : "
                        f"section {sec} mm² < minimum NF C 15-100 {min_sec} mm²."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    fields_compared={
                        "section_mm2": sec,
                        "min_norme_mm2": min_sec,
                        "calibre_A": cl.calibre,
                    },
                    norm_rule_code=rule["id"],
                    suggested_action=(
                        f"Augmenter la section a au moins {min_sec} mm² "
                        f"conformement a {rule.get('source', 'NF C 15-100')}."
                    ),
                )

    def _check_pe_section(self, rule: dict, lines: list[CanecoLine]) -> None:
        for cl in lines:
            if _is_tableau_line(cl):
                continue
            phase_sec = parse_caneco_cable(cl.cable)
            if phase_sec is None:
                continue
            pe_str = cl.pe
            if not pe_str:
                continue
            pe_sec = parse_caneco_pe_section(cl.cable, phase_sec)
            if pe_sec is None:
                try:
                    pe_sec = float(pe_str.replace(",", ".").strip().lstrip("gG"))
                except ValueError:
                    continue

            min_pe = min_pe_section(phase_sec)
            if pe_sec < min_pe * 0.95:
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=rule["name"],
                    severity=_SEVERITY_MAP.get(rule["severity"], BLOQUANT),
                    description=(
                        f"Circuit '{cl.repere or '—'}' : PE = {pe_sec} mm² "
                        f"inferieur au minimum NF C 15-100 ({min_pe} mm² "
                        f"pour phase {phase_sec} mm²)."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    fields_compared={
                        "pe_mm2": pe_sec,
                        "min_pe_norme_mm2": min_pe,
                        "phase_mm2": phase_sec,
                    },
                    norm_rule_code=rule["id"],
                    suggested_action=(
                        f"Augmenter le conducteur PE a au moins {min_pe} mm²."
                    ),
                )

    def _check_calibre_vs_ib(self, rule: dict, lines: list[CanecoLine]) -> None:
        # Traite par ProtectionChecker
        pass

    def _check_neutral_section_monophase(self, rule: dict, lines: list[CanecoLine]) -> None:
        for cl in lines:
            if _is_tableau_line(cl):
                continue
            nb = parse_caneco_conductors(cl.cable)
            if nb is None or nb != 2:
                continue
            phase_sec = parse_caneco_cable(cl.cable)
            if phase_sec is None:
                continue
            neutre_str = cl.neutre
            if not neutre_str:
                continue
            try:
                n_sec = float(neutre_str.replace(",", ".").strip().lstrip("gGnN"))
            except ValueError:
                continue
            if n_sec < phase_sec * 0.95:
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=rule["name"],
                    severity=_SEVERITY_MAP.get(rule["severity"], BLOQUANT),
                    description=(
                        f"Circuit monophase '{cl.repere or '—'}' : neutre {n_sec} mm² "
                        f"< phase {phase_sec} mm². "
                        f"NF C 15-100 exige neutre = phase en monophase."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    fields_compared={"neutre_mm2": n_sec, "phase_mm2": phase_sec},
                    norm_rule_code=rule["id"],
                    suggested_action="Augmenter la section neutre a la valeur de la section de phase.",
                )

    def _check_voltage_drop_by_style(self, rule: dict, lines: list[CanecoLine]) -> None:
        """Signal chute de tension pour circuits longs.

        CORRECTION v1.1 : severite forcee a A_SIGNALER (on n'a pas la valeur reelle de dU%),
        seuil longueur passe a 50 m pour reduire le bruit.
        """
        params = rule.get("parameters", {})
        keywords = params.get("style_keywords", [])
        excluded = params.get("style_keywords_excluded", [])
        max_drop = params.get("max_voltage_drop_pct")
        if max_drop is None:
            return

        for cl in lines:
            if _is_tableau_line(cl):
                continue
            if excluded and _style_matches(cl.style, excluded):
                continue
            if keywords and not _style_matches(cl.style, keywords):
                continue
            if not (cl.longueur and cl.longueur >= _LONGUEUR_THRESHOLD_DT):
                continue
            self._emitter.emit(
                code=rule["gap_code"],
                title=f"Chute de tension a verifier — circuit long ({cl.longueur:.0f} m)",
                # Toujours A_SIGNALER : on ne connait pas dU% reel depuis cet export
                severity=A_SIGNALER,
                description=(
                    f"Circuit '{cl.repere or '—'}' (longueur {cl.longueur:.0f} m) : "
                    f"verifier que la chute de tension reste <= {max_drop} % "
                    f"conformement a {rule.get('source', 'NF C 15-100')}. "
                    f"La valeur exacte de dU% n'est pas disponible dans l'export CANECO."
                ),
                caneco_line_id=cl.id,
                caneco_repere=cl.repere,
                fields_compared={
                    "longueur_m": cl.longueur,
                    "limite_pct": max_drop,
                    "seuil_alerte_m": _LONGUEUR_THRESHOLD_DT,
                },
                norm_rule_code=rule["id"],
                suggested_action=(
                    "Ouvrir CANECO et relever la colonne dU% pour ce circuit. "
                    f"Si > {max_drop} %, augmenter la section ou raccourcir le cable."
                ),
            )

    def _check_icu_vs_icc_presumed(self, rule: dict, lines: list[CanecoLine]) -> None:
        # Traite par ProtectionChecker
        pass

    def _check_ddr_required_by_style(self, rule: dict, lines: list[CanecoLine]) -> None:
        """DDR obligatoire par type de circuit.

        CORRECTION v1.1 : si la regle a context='habitation', la severite est abaissee a
        A_SIGNALER et le titre precise le contexte. Cela evite les faux positifs BLOQUANT
        sur les installations tertiaires/industrielles (ex. DACHSER).
        """
        params = rule.get("parameters", {})
        keywords = params.get("style_keywords", [])
        cal_max = params.get("calibre_max_a")
        req_sens = params.get("required_ddr_sensitivity_ma")
        context = params.get("context", "")
        is_habitation_only = "habitation" in context.lower() if context else False
        if not keywords or req_sens is None:
            return

        # Severite : BLOQUANT en general, A_SIGNALER si contexte habitation uniquement
        effective_sev = A_SIGNALER if is_habitation_only else _SEVERITY_MAP.get(rule["severity"], A_CORRIGER)
        ctx_note = " (regle applicable en habitation — a verifier selon le type d'installation)" if is_habitation_only else ""

        for cl in lines:
            if _is_tableau_line(cl):
                continue
            if not _style_matches(cl.style, keywords):
                continue
            if cal_max and (cl.calibre is None or cl.calibre > cal_max):
                continue
            diff = cl.bloc_differentiel or ""
            if not diff:
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=f"{rule['name']}{ctx_note}",
                    severity=effective_sev,
                    description=(
                        f"Circuit '{cl.repere or '—'}' ({cl.style}) : "
                        f"aucune protection differentielle {req_sens:.0f} mA renseignee dans CANECO."
                        f"{ctx_note}"
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    fields_compared={"bloc_differentiel": diff or None, "requis_mA": req_sens},
                    norm_rule_code=rule["id"],
                    suggested_action=(
                        f"Verifier si un DDR {req_sens:.0f} mA est prevu en tete de tableau "
                        f"ou directement sur ce circuit."
                        f" {ctx_note}"
                    ),
                )

    def _check_ddr_required_by_location(self, rule: dict, lines: list[CanecoLine]) -> None:
        params = rule.get("parameters", {})
        loc_keywords = params.get("location_keywords", [])
        req_sens = params.get("required_ddr_sensitivity_ma")
        if not loc_keywords or req_sens is None:
            return

        for cl in lines:
            desig = (cl.designation or "").lower()
            style = (cl.style or "").lower()
            if not any(k.lower() in desig or k.lower() in style for k in loc_keywords):
                continue
            diff = cl.bloc_differentiel or ""
            if not diff:
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=rule["name"],
                    severity=_SEVERITY_MAP.get(rule["severity"], BLOQUANT),
                    description=(
                        f"Circuit '{cl.repere or '—'}' en local humide : "
                        f"aucune protection differentielle {req_sens:.0f} mA renseignee."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    fields_compared={"bloc_differentiel": diff or None, "requis_mA": req_sens},
                    norm_rule_code=rule["id"],
                    suggested_action=(
                        f"Ajouter un DDR {req_sens:.0f} mA — obligatoire en local contenant "
                        f"une douche ou baignoire."
                    ),
                )

    def _check_selectivity_ratio(self, rule: dict, lines: list[CanecoLine]) -> None:
        params = rule.get("parameters", {})
        min_ratio = params.get("min_ratio_imag_amont_aval", 1.5)
        index: dict[str, CanecoLine] = {}
        for cl in lines:
            if cl.repere:
                index[cl.repere.strip().upper()] = cl

        for cl in lines:
            amont_repere = (cl.amont or "").strip().upper()
            if not amont_repere:
                continue
            cl_amont = index.get(amont_repere)
            if cl_amont is None:
                continue

            # Exclut les lignes avec IrMg hors plage valide
            if cl.ir_mg_in is None or cl.ir_mg_in > _IRMG_MAX:
                continue
            if cl_amont.ir_mg_in is None or cl_amont.ir_mg_in > _IRMG_MAX:
                continue

            imag_cl = (cl.ir_mg_in or 0) * (cl.calibre or 0)
            imag_amont = (cl_amont.ir_mg_in or 0) * (cl_amont.calibre or 0)

            if imag_cl <= 0 or imag_amont <= 0:
                continue

            if imag_amont < imag_cl * min_ratio:
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=rule["name"],
                    severity=_SEVERITY_MAP.get(rule["severity"], A_CORRIGER),
                    description=(
                        f"Selectivite insuffisante : circuit '{cl.repere}' "
                        f"(IrMg×In = {imag_cl:.0f} A) "
                        f"vs amont '{cl_amont.repere}' (IrMg×In = {imag_amont:.0f} A). "
                        f"Ratio = {imag_amont / imag_cl:.2f} < {min_ratio}."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    fields_compared={
                        "imag_aval_A": round(imag_cl, 1),
                        "imag_amont_A": round(imag_amont, 1),
                        "ratio": round(imag_amont / imag_cl, 2),
                        "ratio_min": min_ratio,
                    },
                    norm_rule_code=rule["id"],
                    suggested_action=(
                        "Augmenter le calibre ou le reglage IrMg de la protection amont "
                        "pour assurer la selectivite amperemetrique."
                    ),
                )

    def _check_tripping_curve_check(self, rule: dict, lines: list[CanecoLine]) -> None:
        """Verification de la courbe de declenchement.

        CORRECTION v1.1 :
        - Utilise classify_tripping_curve() qui exclut les valeurs IrMg/IN > 20
          (donnees aberrantes ou hors plage normative — pas de signal emis).
        - Evite les faux positifs sur les grandes installations industrielles.
        """
        params = rule.get("parameters", {})
        keywords = params.get("style_keywords", [])
        recommended = params.get("recommended_curve")
        if not keywords or not recommended:
            return

        for cl in lines:
            if _is_tableau_line(cl):
                continue
            if not _style_matches(cl.style, keywords):
                continue
            ir_mg = cl.ir_mg_in
            if ir_mg is None:
                continue

            current_curve = classify_tripping_curve(ir_mg)
            if current_curve is None:
                # IrMg/IN hors plage valide (> 20 ou <= 0) — donnee suspecte, pas de signal
                continue

            if current_curve != recommended:
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=rule["name"],
                    severity=_SEVERITY_MAP.get(rule["severity"], A_SIGNALER),
                    description=(
                        f"Circuit '{cl.repere or '—'}' ({cl.style}) : "
                        f"courbe actuelle '{current_curve}' (IrMg/IN = {ir_mg:.1f}) "
                        f"— courbe recommandee '{recommended}'."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    fields_compared={
                        "courbe_actuelle": current_curve,
                        "courbe_recommandee": recommended,
                        "IrMg_In": ir_mg,
                    },
                    norm_rule_code=rule["id"],
                    suggested_action=(
                        f"Modifier la courbe de declenchement vers '{recommended}' "
                        f"pour ce type de circuit."
                    ),
                )

    def _check_min_section_by_material(self, rule: dict, lines: list[CanecoLine]) -> None:
        params = rule.get("parameters", {})
        mat_kw = params.get("material_keyword", "Al")
        min_sec = params.get("min_section_mm2")
        if min_sec is None:
            return

        for cl in lines:
            if _is_tableau_line(cl):
                continue
            mat = normalize_material(cl.ame)
            if mat != normalize_material(mat_kw):
                continue
            sec = parse_caneco_cable(cl.cable)
            if sec is not None and sec < min_sec:
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=rule["name"],
                    severity=_SEVERITY_MAP.get(rule["severity"], BLOQUANT),
                    description=(
                        f"Circuit '{cl.repere or '—'}' en aluminium : "
                        f"section {sec} mm² < minimum {min_sec} mm² "
                        f"impose par NF C 15-100."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    fields_compared={"section_mm2": sec, "min_norme_mm2": min_sec, "materiau": mat},
                    norm_rule_code=rule["id"],
                    suggested_action=(
                        f"Remplacer le conducteur aluminium par un cable >= {min_sec} mm² "
                        f"ou utiliser du cuivre pour les petites sections."
                    ),
                )

    def _check_ddr_type_by_load(self, rule: dict, lines: list[CanecoLine]) -> None:
        params = rule.get("parameters", {})
        nl_keywords = params.get("style_keywords_nonlinear", [])
        req_type = params.get("required_ddr_type", "A")
        if not nl_keywords:
            return

        for cl in lines:
            if _is_tableau_line(cl):
                continue
            if not _style_matches(cl.style, nl_keywords):
                desig = (cl.designation or "").lower()
                if not any(k.lower() in desig for k in nl_keywords):
                    continue
            diff = (cl.bloc_differentiel or "").upper()
            if not diff:
                continue
            if "AC" in diff and req_type not in diff:
                self._emitter.emit(
                    code=rule["gap_code"],
                    title=rule["name"],
                    severity=_SEVERITY_MAP.get(rule["severity"], A_CORRIGER),
                    description=(
                        f"Circuit '{cl.repere or '—'}' (charge non-lineaire) : "
                        f"DDR type 'AC' — risque de non-declenchement. "
                        f"Utiliser un DDR type '{req_type}'."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    fields_compared={"ddr_type_actuel": "AC", "ddr_type_requis": req_type},
                    norm_rule_code=rule["id"],
                    suggested_action=(
                        f"Remplacer le DDR type AC par un DDR type {req_type} "
                        f"(sensible aux courants pulses redresses)."
                    ),
                )

    # Regles non implementees en V1
    def _check_neutral_section_triphase_harmonic(self, r: dict, l: list[CanecoLine]) -> None:
        pass

    def _check_surge_protection_required(self, r: dict, l: list[CanecoLine]) -> None:
        pass

    def _check_total_voltage_drop(self, r: dict, l: list[CanecoLine]) -> None:
        pass

    def _check_ir_th_vs_iz(self, r: dict, l: list[CanecoLine]) -> None:
        pass

    def _check_ddr_300ma_tertiaire(self, r: dict, l: list[CanecoLine]) -> None:
        pass
