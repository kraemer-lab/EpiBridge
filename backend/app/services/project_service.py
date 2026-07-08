import uuid
from typing import List

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.user import User
from app.schemas.project import ProjectCreate


def list_projects(db: Session, user_id: uuid.UUID) -> List[Project]:
    membership_ids = (
        db.query(ProjectMembership.project_id)
        .filter(ProjectMembership.user_id == user_id)
        .subquery()
    )
    return (
        db.query(Project)
        .filter(Project.id.in_(membership_ids))
        .order_by(Project.name)
        .all()
    )


def create_project(db: Session, data: ProjectCreate, owner_id: uuid.UUID) -> Project:
    project = Project(
        name=data.name,
        description=data.description,
        owner_id=owner_id,
    )
    db.add(project)
    db.flush()

    membership = ProjectMembership(
        project_id=project.id,
        user_id=owner_id,
        created_by_id=owner_id,
    )
    db.add(membership)
    db.commit()
    db.refresh(project)
    return project


def add_member(
    db: Session, project_id: uuid.UUID, user: User, invited_by_id: uuid.UUID
) -> ProjectMembership:
    existing = (
        db.query(ProjectMembership)
        .filter(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == user.id,
        )
        .first()
    )
    if existing is not None:
        return existing

    membership = ProjectMembership(
        project_id=project_id,
        user_id=user.id,
        created_by_id=invited_by_id,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def remove_member(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = (
        db.query(ProjectMembership)
        .filter(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == user_id,
        )
        .delete()
    )
    db.commit()
    return result > 0


def list_members(db: Session, project_id: uuid.UUID) -> List[dict]:
    rows = (
        db.query(ProjectMembership, User)
        .join(User, ProjectMembership.user_id == User.id)
        .filter(ProjectMembership.project_id == project_id)
        .order_by(User.display_name)
        .all()
    )
    return [
        {
            "user_id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "added_at": membership.created_at,
        }
        for membership, user in rows
    ]
