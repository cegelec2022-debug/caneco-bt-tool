from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.project import Project
from app.models.user import User, UserRole
from app.repositories import project_repository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _get_project_or_403(project_id: str, db: Session, current_user: User) -> Project:
    project = project_repository.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable.")
    if current_user.role not in (UserRole.ADMIN, UserRole.RA):
        if project.created_by != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")
    return project


@router.get("/", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Project]:
    return project_repository.list_for_user(db, current_user.id, current_user.role)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    if project_repository.get_by_code(db, payload.code):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Un projet avec le code '{payload.code}' existe déjà.",
        )
    return project_repository.create(
        db,
        code=payload.code,
        name=payload.name,
        client=payload.client,
        agency=payload.agency,
        description=payload.description,
        status=payload.status,
        created_by=current_user.id,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    return _get_project_or_403(project_id, db, current_user)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    project = _get_project_or_403(project_id, db, current_user)
    updates = payload.model_dump(exclude_unset=True)
    return project_repository.update(db, project, **updates)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    project = _get_project_or_403(project_id, db, current_user)
    project_repository.delete(db, project)
