import uuid

from sqlalchemy.orm import Session

from app.models.audit_event import AuditEventType
from app.models.data_resource import DataResource
from app.models.terms_acceptance import TermsAcceptance
from app.models.terms_of_service import TermsOfService
from app.models.user import User
from app.services.audit_service import create_audit_event


def publish_platform_terms(
    db: Session,
    *,
    published_by: User,
    title: str,
    content: str,
    version: str,
) -> TermsOfService:
    terms = TermsOfService(
        terms_type="platform",
        version=version,
        title=title,
        content=content,
        published_by_id=published_by.id,
    )
    db.add(terms)
    db.flush()

    create_audit_event(
        db,
        event_type=AuditEventType.PLATFORM_TERMS_PUBLISHED,
        actor_id=published_by.id,
        resource_type="terms_of_service",
        resource_id=terms.id,
        metadata={
            "version": version,
            "title": title,
        },
    )

    accept_terms(db, user=published_by, terms_of_service=terms)

    db.commit()
    db.refresh(terms)
    return terms


def publish_resource_terms(
    db: Session,
    *,
    published_by: User,
    data_resource_id: uuid.UUID,
    title: str,
    content: str,
    version: str,
) -> TermsOfService:
    resource = (
        db.query(DataResource).filter(DataResource.id == data_resource_id).first()
    )
    if resource is None:
        raise ValueError(f"Data resource not found: {data_resource_id}")

    terms = TermsOfService(
        terms_type="data_resource",
        data_resource_id=data_resource_id,
        version=version,
        title=title,
        content=content,
        published_by_id=published_by.id,
    )
    db.add(terms)
    db.flush()

    create_audit_event(
        db,
        event_type=AuditEventType.DATASET_TERMS_PUBLISHED,
        actor_id=published_by.id,
        resource_type="terms_of_service",
        resource_id=terms.id,
        metadata={
            "version": version,
            "title": title,
            "data_resource_id": str(data_resource_id),
        },
    )

    accept_terms(db, user=published_by, terms_of_service=terms)

    db.commit()
    db.refresh(terms)
    return terms


def accept_terms(
    db: Session,
    *,
    user: User,
    terms_of_service: TermsOfService,
) -> TermsAcceptance:
    existing = (
        db.query(TermsAcceptance)
        .filter(
            TermsAcceptance.user_id == user.id,
            TermsAcceptance.terms_of_service_id == terms_of_service.id,
        )
        .first()
    )
    if existing is not None:
        return existing

    acceptance = TermsAcceptance(
        user_id=user.id,
        terms_of_service_id=terms_of_service.id,
    )
    db.add(acceptance)

    event_type = (
        AuditEventType.PLATFORM_TERMS_ACCEPTED
        if terms_of_service.terms_type == "platform"
        else AuditEventType.DATASET_TERMS_ACCEPTED
    )

    create_audit_event(
        db,
        event_type=event_type,
        actor_id=user.id,
        resource_type="terms_of_service",
        resource_id=terms_of_service.id,
        metadata={
            "version": terms_of_service.version,
            "title": terms_of_service.title,
        },
    )

    return acceptance


def get_current_platform_terms(db: Session) -> TermsOfService | None:
    return (
        db.query(TermsOfService)
        .filter(TermsOfService.terms_type == "platform")
        .order_by(TermsOfService.published_at.desc())
        .first()
    )


def get_current_resource_terms(
    db: Session, data_resource_id: uuid.UUID
) -> TermsOfService | None:
    return (
        db.query(TermsOfService)
        .filter(
            TermsOfService.terms_type == "data_resource",
            TermsOfService.data_resource_id == data_resource_id,
        )
        .order_by(TermsOfService.published_at.desc())
        .first()
    )


def has_accepted_latest(
    db: Session, user_id: uuid.UUID, terms_of_service_id: uuid.UUID
) -> bool:
    return (
        db.query(TermsAcceptance)
        .filter(
            TermsAcceptance.user_id == user_id,
            TermsAcceptance.terms_of_service_id == terms_of_service_id,
        )
        .first()
        is not None
    )


def get_acceptance_status(db: Session, user_id: uuid.UUID) -> dict:
    platform_terms = get_current_platform_terms(db)
    platform_accepted = False
    platform_version = None
    if platform_terms is not None:
        platform_version = platform_terms.version
        platform_accepted = has_accepted_latest(db, user_id, platform_terms.id)

    resource_id_rows = (
        db.query(TermsOfService.data_resource_id)
        .filter(
            TermsOfService.terms_type == "data_resource",
            TermsOfService.data_resource_id.isnot(None),
        )
        .distinct()
        .all()
    )

    dataset_terms = []
    for (rid,) in resource_id_rows:
        terms = get_current_resource_terms(db, rid)
        if terms is not None:
            accepted = has_accepted_latest(db, user_id, terms.id)
            dataset_terms.append(
                {
                    "resource_id": str(rid),
                    "version": terms.version,
                    "title": terms.title,
                    "accepted": accepted,
                }
            )

    return {
        "platform": {
            "has_terms": platform_terms is not None,
            "version": platform_version,
            "accepted": platform_accepted,
        },
        "dataset_terms": dataset_terms,
    }
