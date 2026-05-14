"""Moteur de verification croisee CANECO + Bordereau + CPS.

Orchestrateur principal : enchaîne les 6 checkers dans l'ordre, persiste
le VerificationRun et ses Gaps en base, et retourne le run complete.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.caneco import CanecoLine
from app.models.bordereau import BordereauLine
from app.models.cps import CpsImport
from app.models.project import Project
from app.models.verification import Gap, VerificationRun
from app.services.verification.cable_comparator import CableComparator
from app.services.verification.cps_checker import CpsChecker
from app.services.verification.gap_emitter import BLOQUANT, A_CORRIGER, A_SIGNALER, GapEmitter
from app.services.verification.line_matcher import LineMatcher
from app.services.verification.norm_checker import NormChecker
from app.services.verification.protection_checker import (
    ProtectionChecker,
    compute_depth_map,
)
from app.services.verification.suggestion_engine import SuggestionEngine


def run_verification(
    *,
    db: Session,
    project_id: str,
    caneco_export_id: str,
    bordereau_import_id: str,
    cps_import_id: str | None = None,
    triggered_by: str = "manual",
    created_by_id: str | None = None,
    icc_presumed_ka: float | None = None,
) -> VerificationRun:
    """Lance le moteur de verification et retourne le VerificationRun persiste.

    Args:
        db: Session SQLAlchemy.
        project_id: Identifiant du projet.
        caneco_export_id: Export CANECO a verifier.
        bordereau_import_id: Bordereau de reference.
        cps_import_id: CPS optionnel (comparaison regles).
        triggered_by: 'manual' ou 'auto'.
        created_by_id: Utilisateur declencheur.
        icc_presumed_ka: Courant de court-circuit presume (kA). Defaut = 6 kA.

    Returns:
        VerificationRun avec statut 'done' ou 'error'.
    """
    # Charge le projet pour recuperer le domaine d'installation (conditionne certaines regles)
    project: Project | None = db.get(Project, project_id)
    domaine = (project.domaine_installation if project else "tertiaire") or "tertiaire"

    run = VerificationRun(
        id=str(uuid.uuid4()),
        project_id=project_id,
        caneco_export_id=caneco_export_id,
        bordereau_import_id=bordereau_import_id,
        cps_import_id=cps_import_id,
        status="running",
        triggered_by=triggered_by,
        created_by_id=created_by_id,
        config_snapshot={
            "icc_presumed_ka": icc_presumed_ka or 6.0,
            "domaine_installation": domaine,
            "engine_version": "1.2",
        },
    )
    db.add(run)
    db.flush()

    start_time = time.monotonic()

    try:
        # --- 1. Charge les donnees ---
        caneco_lines: list[CanecoLine] = (
            db.query(CanecoLine)
            .filter(CanecoLine.export_id == caneco_export_id)
            .all()
        )
        bordereau_lines: list[BordereauLine] = (
            db.query(BordereauLine)
            .filter(BordereauLine.bordereau_import_id == bordereau_import_id)
            .all()
        )
        cps_rules: list[dict] = []
        if cps_import_id:
            cps_imp: CpsImport | None = db.get(CpsImport, cps_import_id)
            if cps_imp and cps_imp.extracted_rules:
                cps_rules = cps_imp.extracted_rules

        # --- 2. Initialise le collecteur d'ecarts ---
        emitter = GapEmitter()

        # --- 3. Rapprochement CANECO <-> Bordereau ---
        matcher = LineMatcher(caneco_lines, bordereau_lines, emitter)
        match_report = matcher.run()

        # --- 4. Comparaison cables ---
        cable_comp = CableComparator(emitter)
        cable_comp.run(match_report.matched)

        # --- 5. Verification protections ---
        # Icc degressif par profondeur : on calcule la profondeur de chaque ligne dans
        # l'arborescence des tableaux, puis Icc(ligne) = Icc_origine × decay^profondeur.
        depth_map = compute_depth_map(caneco_lines)
        prot_checker = ProtectionChecker(
            emitter,
            icc_presumed_ka=icc_presumed_ka,
            depth_map=depth_map,
        )
        prot_checker.run(caneco_lines)

        # --- 6. Regles NF C 15-100 ---
        # Le domaine d'installation conditionne l'application de certaines regles
        # (ex. NFC-012 DDR prises 30 mA est specifique a l'habitation)
        norm_checker = NormChecker(emitter, domaine_installation=domaine)
        norm_checker.run(caneco_lines)

        # --- 7. Regles CPS (si disponible) ---
        if cps_rules:
            cps_checker = CpsChecker(emitter, cps_rules)
            cps_checker.run(caneco_lines)

        # --- 8. Suggestions bonnes pratiques ---
        sug_engine = SuggestionEngine(emitter)
        sug_engine.run(caneco_lines)

        # --- 9. Persiste les gaps ---
        gaps_dtos = emitter.gaps
        for dto in gaps_dtos:
            gap = Gap(
                id=dto.id,
                run_id=run.id,
                code=dto.code,
                title=dto.title,
                severity=dto.severity,
                description=dto.description,
                fields_compared=dto.fields_compared,
                suggested_action=dto.suggested_action,
                norm_rule_code=dto.norm_rule_code,
                caneco_line_id=dto.caneco_line_id,
                bordereau_line_id=dto.bordereau_line_id,
                caneco_repere=dto.caneco_repere,
                caneco_amont=dto.caneco_amont,
                caneco_row=dto.caneco_row,
                bordereau_num_prix=dto.bordereau_num_prix,
                bordereau_row=dto.bordereau_row,
            )
            db.add(gap)

        # --- 10. Met a jour les compteurs du run ---
        counts = emitter.count_by_severity()
        run.total_gaps = len(gaps_dtos)
        run.critical_count = counts.get(BLOQUANT, 0)
        run.high_count = counts.get(A_CORRIGER, 0)
        run.medium_count = counts.get(A_SIGNALER, 0)
        run.info_count = counts.get("INFO", 0)
        run.status = "done"
        run.duration_seconds = time.monotonic() - start_time

    except Exception as exc:  # noqa: BLE001
        run.status = "error"
        run.error_message = str(exc)[:500]
        run.duration_seconds = time.monotonic() - start_time

    db.commit()
    db.refresh(run)
    return run
