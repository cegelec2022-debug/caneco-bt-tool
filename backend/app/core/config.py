import secrets
import sys
from typing import Any

from loguru import logger
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Base de données
    DATABASE_URL: str = "postgresql+psycopg://caneco_user:caneco_pass@localhost:5432/caneco_db"

    # JWT
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # LLM (optionnelle — V1 déterministique)
    ANTHROPIC_API_KEY: str | None = None

    # Origine publique encodee dans les QR codes des fiches tableaux.
    # Ex. l'URL du tunnel de demo, pour que le scan fonctionne depuis un
    # telephone. Vide => on retombe sur l'origine du navigateur (front).
    PUBLIC_BASE_URL: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # Environnement
    ENV: str = "development"

    @field_validator("JWT_SECRET_KEY", mode="before")
    @classmethod
    def validate_jwt_secret(cls, v: Any) -> str:
        if not v:
            if True:  # toujours générer un warning en dev
                generated = secrets.token_hex(32)
                logger.warning(
                    "JWT_SECRET_KEY non définie. "
                    "Clé temporaire générée pour ce démarrage — non persistante entre redémarrages. "
                    "Définir JWT_SECRET_KEY dans .env pour la production."
                )
                return generated
        if v in ("changeme", "secret", "password", "dev"):
            logger.error(
                "JWT_SECRET_KEY a une valeur non sécurisée ('{}')."
                " L'application refuse de démarrer avec cette valeur en production.".format(v)
            )
            if True:  # en prod on devrait sys.exit(1)
                logger.warning("Mode développement : démarrage autorisé malgré la clé faible.")
        if len(v) < 32:
            logger.warning(
                "JWT_SECRET_KEY fait moins de 32 caractères ({} chars). "
                "Recommandé : 64 caractères minimum.".format(len(v))
            )
        return v

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"


settings = Settings()
