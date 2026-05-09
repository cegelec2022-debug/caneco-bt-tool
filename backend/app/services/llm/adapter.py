"""
Adapter LLM — interface entre le moteur de vérification et les APIs LLM.

Architecture V1/V2 :
- V1 (actuel) : DeterministicAdapter — 100 % Python, aucun appel réseau.
  Formulation des écarts par templates, extraction CPS par regex.
- V2 (futur) : AnthropicAdapter — activé si ANTHROPIC_API_KEY est présente dans .env.
  Aucune modification du moteur de vérification requise pour le passage en V2.

Pour activer le LLM : ajouter ANTHROPIC_API_KEY dans .env et appeler get_adapter().
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class LlmAdapter(ABC):
    """Interface commune. Le moteur de vérification ne connaît que cette interface."""

    @abstractmethod
    def format_gap_message(self, gap_code: str, context: dict) -> str:
        """Formule le message d'un écart en langage naturel lisible par un ingénieur."""
        ...

    @abstractmethod
    def extract_cps_rules(self, cps_text: str) -> list[dict]:
        """Extrait les règles chiffrables d'un texte de CPS.

        Returns:
            Liste de règles au format :
            [{"type": str, "value": float | str, "unit": str, "raw": str}]
        """
        ...


class DeterministicAdapter(LlmAdapter):
    """Implémentation déterministique — V1. Utilisée quand ANTHROPIC_API_KEY est absente."""

    _GAP_TEMPLATES: dict[str, str] = {
        "E-001": "Circuit {repere} présent dans CANECO mais absent du bordereau.",
        "E-002": "Circuit {repere} présent dans le bordereau mais absent de CANECO.",
        "E-003": (
            "Écart de section pour le circuit {repere} : "
            "CANECO indique {section_caneco}, bordereau indique {section_bordereau}."
        ),
        "E-004": (
            "Écart de calibre de protection pour {repere} : "
            "CANECO {calibre_caneco} A, bordereau {calibre_bordereau} A."
        ),
        "E-005": (
            "Type de câble en désaccord pour {repere} : "
            "CANECO {type_caneco}, bordereau {type_bordereau}."
        ),
        "E-006": (
            "Écart de longueur sur {repere} : "
            "prévue {longueur_prevue} m, réalisée {longueur_realisee} m "
            "(écart {ecart_pct:.1f} %)."
        ),
        "E-007": (
            "Type de câble non conforme au CPS pour {repere} : "
            "imposé {type_impose}, utilisé {type_utilise}."
        ),
        "E-008": (
            "Section inférieure au minimum NF C 15-100 pour {repere} : "
            "{section_utilisee} mm², minimum requis {section_min} mm² ({source})."
        ),
        "E-009": (
            "Chute de tension dépassée pour {repere} : "
            "calculée {chute_calculee:.2f} %, seuil {chute_max:.2f} % ({source})."
        ),
        "E-010": "{message}",
    }

    def format_gap_message(self, gap_code: str, context: dict) -> str:
        template = self._GAP_TEMPLATES.get(
            gap_code, "Écart {gap_code} détecté sur {repere}."
        )
        try:
            return template.format(**context)
        except KeyError:
            return f"Écart {gap_code} détecté sur {context.get('repere', '?')}."

    def extract_cps_rules(self, cps_text: str) -> list[dict]:
        # L'extraction par regex est dans CpsRuleExtractor. Cet adapter délègue.
        return []


class AnthropicAdapter(LlmAdapter):
    """Adapter Anthropic Claude — V2. Non instancié si ANTHROPIC_API_KEY est absente."""

    def __init__(self, api_key: str) -> None:
        try:
            import anthropic  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "Package 'anthropic' non installé. "
                "Ajouter 'anthropic' à requirements.txt et relancer Docker."
            ) from exc
        self._client = anthropic.Anthropic(api_key=api_key)

    def format_gap_message(self, gap_code: str, context: dict) -> str:
        raise NotImplementedError("AnthropicAdapter.format_gap_message — implémentation V2.")

    def extract_cps_rules(self, cps_text: str) -> list[dict]:
        raise NotImplementedError("AnthropicAdapter.extract_cps_rules — implémentation V2.")


def get_adapter(api_key: Optional[str] = None) -> LlmAdapter:
    """Retourne l'adapter selon la configuration.

    V1 : DeterministicAdapter (aucune clé requise).
    V2 : AnthropicAdapter si ANTHROPIC_API_KEY est présente.
    """
    if api_key:
        return AnthropicAdapter(api_key)
    return DeterministicAdapter()
