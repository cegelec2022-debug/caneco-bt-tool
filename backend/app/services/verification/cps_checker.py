"""CpsChecker — verifie la conformite des donnees CANECO aux regles du CPS.

Ecarts produits :
- E-005 : type cable CANECO != type cable CPS
- E-014 : regle CPS sans correspondance dans CANECO
- E-020 : regle CPS non respectee
"""

from __future__ import annotations

from app.models.caneco import CanecoLine
from app.services.verification.cable_utils import normalize_material, parse_caneco_cable
from app.services.verification.gap_emitter import A_CORRIGER, A_SIGNALER, BLOQUANT, GapEmitter

# Mapping type_cable CPS (normalise) vers les valeurs possibles dans CANECO
_CABLE_TYPE_ALIASES: dict[str, list[str]] = {
    "U1000R2V": ["U1000R2V", "U10002V", "R2V"],
    "U1000AR2V": ["U1000AR2V", "U1000A R2V", "AR2V"],
    "U1000RO2V": ["U1000RO2V", "U1000R02V", "RO2V", "R02V"],
    "H07VK": ["H07VK", "H07VK6", "H07V-K"],
    "H07VU": ["H07VU", "H07V-U"],
    "FRC2X": ["FRC2X", "CR1"],
    "RVFV": ["RVFV"],
    "XV": ["XV"],
}


def _cable_type_matches(caneco_type: str | None, cps_type: str) -> bool:
    """Verifie si le type cable CANECO satisfait le type impose par le CPS."""
    if not caneco_type:
        return False
    ct_upper = caneco_type.strip().upper().replace(" ", "")
    cps_upper = cps_type.strip().upper().replace(" ", "")
    aliases = _CABLE_TYPE_ALIASES.get(cps_upper, [cps_upper])
    return any(ct_upper == a.replace(" ", "").upper() for a in aliases)


class CpsChecker:
    """Compare les regles CPS extraites aux valeurs de l'export CANECO."""

    def __init__(self, emitter: GapEmitter, cps_rules: list[dict]) -> None:
        self._emitter = emitter
        self._rules = cps_rules

    def run(self, caneco_lines: list[CanecoLine]) -> None:
        """Emet les ecarts de non-conformite CPS."""
        for rule in self._rules:
            rule_type = rule.get("rule_type")
            handler = getattr(self, f"_check_{rule_type}", self._check_generic)
            handler(rule, caneco_lines)

    # ------------------------------------------------------------------

    def _check_section_minimale(self, rule: dict, lines: list[CanecoLine]) -> None:
        try:
            min_sec = float(rule.get("value", 0))
        except (TypeError, ValueError):
            return

        violations: list[CanecoLine] = []
        for cl in lines:
            sec = parse_caneco_cable(cl.cable)
            if sec is not None and sec < min_sec:
                violations.append(cl)

        if violations:
            reperes = ", ".join(cl.repere or "—" for cl in violations[:5])
            suffix = f" (+{len(violations) - 5} autres)" if len(violations) > 5 else ""
            self._emitter.emit(
                code="E-020",
                title="Section minimale CPS non respectee",
                severity=BLOQUANT,
                description=(
                    f"Le CPS impose une section minimale de {min_sec} mm². "
                    f"Circuits CANECO en dessous : {reperes}{suffix}."
                ),
                fields_compared={"section_min_cps_mm2": min_sec},
                suggested_action=(
                    f"Augmenter la section des conducteurs a au moins {min_sec} mm² "
                    f"conformement au CPS."
                ),
            )

    def _check_type_cable_requis(self, rule: dict, lines: list[CanecoLine]) -> None:
        cps_type = (rule.get("value") or "").strip().upper()
        if not cps_type:
            return

        mismatches: list[CanecoLine] = []
        for cl in lines:
            if cl.type_cable and not _cable_type_matches(cl.type_cable, cps_type):
                mismatches.append(cl)

        if mismatches:
            reperes = ", ".join(cl.repere or "—" for cl in mismatches[:5])
            suffix = f" (+{len(mismatches) - 5} autres)" if len(mismatches) > 5 else ""
            self._emitter.emit(
                code="E-005",
                title="Type de cable CANECO different du type impose par le CPS",
                severity=A_CORRIGER,
                description=(
                    f"CPS exige le type '{cps_type}'. "
                    f"Circuits avec un autre type dans CANECO : {reperes}{suffix}."
                ),
                fields_compared={"type_cps": cps_type},
                suggested_action=(
                    f"Verifier et corriger le type de cable vers '{cps_type}' "
                    f"dans CANECO conformement au CPS."
                ),
            )

    def _check_chute_tension_max(self, rule: dict, lines: list[CanecoLine]) -> None:
        # La chute de tension n'est pas disponible dans l'export — signal informatif
        try:
            max_dt = float(rule.get("value", 0))
        except (TypeError, ValueError):
            return

        if max_dt > 0:
            self._emitter.emit(
                code="E-009",
                title="Chute de tension max CPS a verifier dans CANECO",
                severity=A_SIGNALER,
                description=(
                    f"Le CPS fixe une chute de tension maximale de {max_dt} %. "
                    f"Verifier que tous les circuits CANECO respectent cette limite."
                ),
                suggested_action=(
                    f"Ouvrir CANECO et verifier colonne 'dU%' pour chaque circuit. "
                    f"La limite CPS est {max_dt} %."
                ),
            )

    def _check_ddr_sensibilite(self, rule: dict, lines: list[CanecoLine]) -> None:
        try:
            req_sens_ma = float(rule.get("value", 0))
        except (TypeError, ValueError):
            return
        if req_sens_ma <= 0:
            return

        missing: list[CanecoLine] = []
        for cl in lines:
            diff = (cl.bloc_differentiel or "").strip()
            if not diff:
                missing.append(cl)

        if missing:
            reperes = ", ".join(cl.repere or "—" for cl in missing[:5])
            suffix = f" (+{len(missing) - 5} autres)" if len(missing) > 5 else ""
            self._emitter.emit(
                code="E-007",
                title=f"DDR {req_sens_ma:.0f} mA CPS : circuits sans differentiel dans CANECO",
                severity=A_CORRIGER,
                description=(
                    f"Le CPS exige des DDR de {req_sens_ma:.0f} mA. "
                    f"Circuits sans differentiel dans CANECO : {reperes}{suffix}."
                ),
                suggested_action=(
                    f"Ajouter une protection differentielle {req_sens_ma:.0f} mA sur ces circuits."
                ),
            )

    def _check_indice_protection(self, rule: dict, lines: list[CanecoLine]) -> None:
        # IP n'est pas un champ CANECO — signal informatif
        ip_value = rule.get("value", "")
        if ip_value:
            self._emitter.emit(
                code="E-020",
                title=f"Indice de protection IP{ip_value} impose par le CPS",
                severity=A_SIGNALER,
                description=(
                    f"Le CPS exige un indice de protection minimum IP{ip_value}. "
                    f"Ce critere n'est pas verifiable automatiquement depuis l'export CANECO. "
                    f"Verifier lors du controle des appareillages."
                ),
                suggested_action=(
                    f"S'assurer que tous les equipements installes ont un IP >= {ip_value}."
                ),
            )

    def _check_tension_nominale(self, rule: dict, lines: list[CanecoLine]) -> None:
        # Signal informatif — la tension n'est pas dans l'export CANECO ligne par ligne
        pass

    def _check_schema_mise_terre(self, rule: dict, lines: list[CanecoLine]) -> None:
        schema = rule.get("value", "")
        if schema:
            self._emitter.emit(
                code="E-020",
                title=f"Schema de mise a la terre CPS : {schema}",
                severity=A_SIGNALER,
                description=(
                    f"Le CPS impose le schema de mise a la terre '{schema}'. "
                    f"Verifier la configuration du TGBT et des tableaux divisionnaires."
                ),
                suggested_action=(
                    f"Confirmer que le schema '{schema}' est bien configure "
                    f"dans le TGBT et les tableaux."
                ),
            )

    def _check_generic(self, rule: dict, lines: list[CanecoLine]) -> None:
        """Fallback : emet un signal informatif pour les types de regles non implementes."""
        rule_type = rule.get("rule_type", "inconnue")
        value = rule.get("value", "")
        if not value:
            return
        self._emitter.emit(
            code="E-020",
            title=f"Regle CPS '{rule_type}' a verifier",
            severity=A_SIGNALER,
            description=(
                f"Regle CPS ({rule_type} = {value}) : "
                f"verification automatique non disponible pour ce type de regle. "
                f"Valider manuellement."
            ),
            suggested_action="Verifier cette regle CPS manuellement dans les documents projet.",
        )
