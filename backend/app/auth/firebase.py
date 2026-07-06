import firebase_admin
from firebase_admin import credentials

from app.core.config import settings


_firebase_app = None


def init_firebase():
    global _firebase_app
    if not settings.firebase_project_id:
        return
    if _firebase_app is None:
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": settings.firebase_project_id,
            "private_key_id": settings.firebase_private_key_id,
            "private_key": settings.firebase_private_key.replace("\\n", "\n"),
            "client_email": settings.firebase_client_email,
            "client_id": settings.firebase_client_id,
        })
        _firebase_app = firebase_admin.initialize_app(cred)
