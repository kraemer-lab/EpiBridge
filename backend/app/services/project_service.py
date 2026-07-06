import uuid
from typing import List

from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate


def list_projects(db: Session, owner_id: uuid.UUID) -> List[Project]:
    return db.query(Project).filter(Project.owner_id == owner_id).all()


def create_project(db: Session, data: ProjectCreate, owner_id: uuid.UUID) -> Project:
    project = Project(
        name=data.name,
        description=data.description,
        owner_id=owner_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
