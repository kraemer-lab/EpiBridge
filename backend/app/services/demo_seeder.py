from sqlalchemy.orm import Session

from app.models.analysis_bundle import (
    AnalysisBundle,
    AnalysisBundleDataResource,
)
from app.models.data_resource import DataResource
from app.models.execution_environment import ExecutionEnvironment
from app.models.project import Project
from app.models.user import User
from app.workflow.bundle import approve_bundle, submit_bundle

DEMO_PROJECT_NAME = "Dengue Analysis Demo"
DEMO_BUNDLE_NAME = "Dengue Summary Statistics"
DEMO_RESOURCE_IDENTIFIER = "mex-dengue-2026"
DEMO_OUTPUT_FILENAME = "summary.csv"


def seed_demo_workspace(db: Session) -> dict:
    admin = db.query(User).filter(User.email == "admin@epibridge.local").first()
    if admin is None:
        return {
            "status": "error",
            "message": "Admin user not found. Run seed-admin first.",
        }

    existing = (
        db.query(Project)
        .filter(Project.name == DEMO_PROJECT_NAME, Project.owner_id == admin.id)
        .first()
    )
    if existing is not None:
        return {
            "status": "skipped",
            "message": (f"Demo workspace already exists (project_id={existing.id})"),
        }

    project = Project(
        name=DEMO_PROJECT_NAME,
        description="Dengue surveillance analysis demo for EpiBridge canonical workflow.",
        owner_id=admin.id,
    )
    db.add(project)
    db.flush()

    resource = (
        db.query(DataResource)
        .filter(DataResource.identifier == DEMO_RESOURCE_IDENTIFIER)
        .first()
    )
    if resource:
        project.data_resources.append(resource)

    env = (
        db.query(ExecutionEnvironment)
        .filter(ExecutionEnvironment.image_reference.isnot(None))
        .filter(ExecutionEnvironment.image_reference != "")
        .order_by(ExecutionEnvironment.created_at)
        .first()
    )
    if env is None:
        env = (
            db.query(ExecutionEnvironment)
            .filter(ExecutionEnvironment.runtime.contains("python"))
            .first()
        )

    bundle = AnalysisBundle(
        project_id=project.id,
        created_by_id=admin.id,
        execution_environment_id=env.id if env else None,
        name=DEMO_BUNDLE_NAME,
        source_path="demo",
        version="1.0.0",
        entrypoint="run.py",
        description=(
            "Computes summary statistics from the Mexico dengue surveillance dataset."
        ),
        outputs=[DEMO_OUTPUT_FILENAME],
        parameters={},
    )
    db.add(bundle)
    db.flush()

    if resource:
        join = AnalysisBundleDataResource(
            analysis_bundle_id=bundle.id,
            data_resource_id=resource.id,
        )
        db.add(join)

    submit_bundle(db, bundle)
    approve_bundle(db, bundle)
    db.commit()

    return {
        "status": "created",
        "project_id": str(project.id),
        "bundle_id": str(bundle.id),
    }
