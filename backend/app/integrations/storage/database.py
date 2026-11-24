"""Stores uploaded and generated images in PostgreSQL. Keys are generated, never user-supplied. Access control is
enforced by the API (media is only served to users who can see its session), not by this class."""
import uuid
from ...core.exceptions import AppError
from ...db.session import SessionLocal
from ...db.models.storage import StoredFile


class StorageError(AppError):
    status, code = 500, 'STORAGE_ERROR'


class DatabaseStorage:
    def put(self, data: bytes, ext: str, prefix: str) -> str:
        key = f'{prefix}/{uuid.uuid4().hex}.{ext}'
        db = SessionLocal()
        try:
            db.add(StoredFile(key=key, data=data, size_bytes=len(data))); db.commit()
        except Exception as e:
            db.rollback(); raise StorageError('Could not save the image. Please try again.') from e
        finally:
            db.close()
        return key

    def get(self, key: str) -> bytes:
        db = SessionLocal()
        try:
            row = db.get(StoredFile, key)
        finally:
            db.close()
        if row is None:
            raise AppError('This image is no longer available.', code='MEDIA_MISSING', status=404)
        return row.data

    def delete(self, key: str) -> None:
        db = SessionLocal()
        try:
            row = db.get(StoredFile, key)
            if row is not None:
                db.delete(row); db.commit()
        finally:
            db.close()
