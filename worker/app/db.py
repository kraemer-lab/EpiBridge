from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Session:
    session = SessionLocal()
    try:
        return session
    except Exception:
        session.close()
        raise


OUTPUT_ROOT = (
    Path(settings.output_dir)
    if hasattr(settings, "output_dir") and settings.output_dir
    else Path("/outputs")
)
ANALYSIS_ROOT = (
    Path(settings.analysis_bundle_root)
    if hasattr(settings, "analysis_bundle_root") and settings.analysis_bundle_root
    else Path("/app/examples/analyses")
)
DATA_ROOT = (
    Path(settings.data_root)
    if hasattr(settings, "data_root") and settings.data_root
    else Path("/read-only-data")
)
