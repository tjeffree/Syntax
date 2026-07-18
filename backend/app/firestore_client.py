"""Shared Firebase Admin / Firestore initialisation for Cloud Run services."""
from __future__ import annotations

from .config import Settings


def get_firestore_client(settings: Settings):
    """Return an Admin-SDK Firestore client using ADC on Cloud Run."""
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        if settings.firebase_credentials:
            firebase_admin.initialize_app(credentials.Certificate(settings.firebase_credentials))
        else:
            firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id} if settings.firebase_project_id else None)
    return firestore.client()
