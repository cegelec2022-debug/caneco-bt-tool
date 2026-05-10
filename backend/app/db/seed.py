from loguru import logger

from app.db.session import SessionLocal
from app.models.user import UserRole
from app.repositories import project_repository, user_repository

_DEMO_USERS = [
    {
        "email": "admin@actemium.fr",
        "password": "Demo2026!",
        "full_name": "Administrateur Actemium",
        "role": UserRole.ADMIN,
    },
    {
        "email": "be@actemium.fr",
        "password": "Demo2026!",
        "full_name": "Mouhcine Benali",
        "role": UserRole.BE,
    },
    {
        "email": "chef@actemium.fr",
        "password": "Demo2026!",
        "full_name": "Mouad Alami",
        "role": UserRole.CHEF_CHANTIER,
    },
    {
        "email": "ra@actemium.fr",
        "password": "Demo2026!",
        "full_name": "Jibrane Mansouri",
        "role": UserRole.RA,
    },
]


def run_seed() -> None:
    db = SessionLocal()
    try:
        # Utilisateurs de démonstration
        admin = None
        for u in _DEMO_USERS:
            existing = user_repository.get_by_email(db, u["email"])
            if not existing:
                created = user_repository.create(
                    db,
                    email=u["email"],
                    password=u["password"],
                    full_name=u["full_name"],
                    role=u["role"],
                )
                logger.info(f"Utilisateur créé : {created.email} ({created.role})")
                if u["role"] == UserRole.ADMIN:
                    admin = created
            else:
                logger.info(f"Utilisateur déjà présent : {existing.email}")
                if existing.role == UserRole.ADMIN:
                    admin = existing

        # Projet pilote DACHSER
        if admin and not project_repository.get_by_code(db, "DACHSER-L3"):
            project = project_repository.create(
                db,
                code="DACHSER-L3",
                name="DACHSER Lot 3 - Électricité",
                client="DACHSER",
                agency="Actemium Cegelec Tanger",
                description="Projet pilote Challenge Innovation VEAO 2026",
                status="actif",
                created_by=admin.id,
            )
            logger.info(f"Projet pilote créé : {project.code}")
        else:
            logger.info("Projet DACHSER-L3 déjà présent.")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
