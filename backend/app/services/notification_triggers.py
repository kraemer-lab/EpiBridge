import uuid
from typing import List

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis_bundle import AnalysisBundle
from app.models.output_set import OutputSet
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.user import User
from app.services.email_service import send_email
from app.services.email_templates import (
    render_bundle_submitted,
    render_output_released,
)


def _get_project_members_with_capability(
    db: Session,
    project_id: uuid.UUID,
    capability: str,
) -> List[User]:
    """Return project members who possess the given capability."""
    memberships = (
        db.query(ProjectMembership)
        .filter(ProjectMembership.project_id == project_id)
        .all()
    )
    user_ids = [m.user_id for m in memberships]
    if not user_ids:
        return []

    users = db.query(User).filter(User.id.in_(user_ids)).all()
    return [u for u in users if u.has_capability(capability)]


def trigger_bundle_submitted_notifications(
    db: Session,
    bundle: AnalysisBundle,
    project: Project,
    submitter: User,
    background_tasks: BackgroundTasks,
) -> None:
    """Notify project moderators that a bundle has been submitted."""
    review_url = f"{settings.public_url}/admin/bundles/{bundle.id}"

    moderators = _get_project_members_with_capability(
        db,
        project.id,
        "bundle.review",
    )
    for moderator in moderators:
        if moderator.id == submitter.id:
            continue

        subject, body = render_bundle_submitted(
            project_name=project.name,
            bundle_name=bundle.name,
            submitter_name=submitter.display_name,
            review_url=review_url,
        )
        background_tasks.add_task(
            send_email,
            moderator.email,
            subject,
            body,
        )


def trigger_output_released_notifications(
    db: Session,
    output_set: OutputSet,
    releaser: User,
    background_tasks: BackgroundTasks,
) -> None:
    """Notify the execution requester and bundle creator that results are
    available.  Duplicate recipients are collapsed into one email."""
    project_id = output_set.execution_request.project_id
    results_url = f"{settings.public_url}/projects/{project_id}/outputs"

    requester = output_set.execution_request.requested_by
    bundle_creator = output_set.execution_request.analysis_bundle.created_by

    recipients: set[User] = set()
    for user in (requester, bundle_creator):
        if user is not None and user.id != releaser.id:
            recipients.add(user)

    if not recipients:
        return

    bundle = output_set.execution_request.analysis_bundle
    project = output_set.execution_request.project

    subject, body = render_output_released(
        project_name=project.name,
        bundle_name=bundle.name,
        results_url=results_url,
    )
    for recipient in recipients:
        background_tasks.add_task(
            send_email,
            recipient.email,
            subject,
            body,
        )
