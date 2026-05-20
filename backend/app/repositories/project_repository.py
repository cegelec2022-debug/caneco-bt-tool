from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.user import UserRole


def list_for_user(db: Session, user_id: str, role: str) -> list[Project]:
    # ADMIN / RA / CHEF_CHANTIER voient tous les projets (le Chef de Chantier
    # intervient sur n'importe quel chantier ouvert ; la gestion fine des
    # assignations chantier est renvoyee a V2).
    if role in (UserRole.ADMIN, UserRole.RA, UserRole.CHEF_CHANTIER):
        return db.query(Project).order_by(Project.created_at.desc()).all()
    return (
        db.query(Project)
        .filter(Project.created_by == user_id)
        .order_by(Project.created_at.desc())
        .all()
    )


def get_by_id(db: Session, project_id: str) -> Project | None:
    return db.query(Project).filter(Project.id == project_id).first()


def get_by_code(db: Session, code: str) -> Project | None:
    return db.query(Project).filter(Project.code == code).first()


def create(
    db: Session,
    *,
    code: str,
    name: str,
    created_by: str,
    client: str | None = None,
    agency: str | None = None,
    description: str | None = None,
    status: str = "actif",
    domaine_installation: str = "tertiaire",
) -> Project:
    project = Project(
        code=code,
        name=name,
        client=client,
        agency=agency,
        description=description,
        status=status,
        domaine_installation=domaine_installation,
        created_by=created_by,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update(db: Session, project: Project, **kwargs: str | None) -> Project:
    for key, value in kwargs.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


def delete(db: Session, project: Project) -> None:
    db.delete(project)
    db.commit()
