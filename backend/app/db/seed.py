from loguru import logger

from app.db.session import SessionLocal
from app.models.user import UserRole
from app.repositories import project_repository, user_repository


def run_seed() -> None:
    db = SessionLocal()
    try:
        admin_email = "admin@actemium.fr"
        admin = user_repository.get_by_email(db, admin_email)
        if not admin:
            admin = user_repository.create(
                db,
                email=admin_email,
                password="Demo2026!",
                full_name="Administrateur Actemium",
                role=UserRole.ADMIN,
            )
            logger.info(f"Utilisateur admin créé : {admin.email}")
        else:
            logger.info("Utilisateur admin déjà présent.")

        if not project_repository.get_by_code(db, "DACHSER-L3"):
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
