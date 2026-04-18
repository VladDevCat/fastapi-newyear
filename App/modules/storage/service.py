import re
import uuid
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from app.common.cache import cache
from app.common.config import settings
from app.common.exceptions import AppException, ForbiddenException, NotFoundException
from app.modules.storage.model import FileRecord
from app.modules.storage.repository import FileRepository
from app.modules.storage.schemas import FileResponseDTO, ProfileResponseDTO, ProfileUpdateDTO
from app.modules.users.model import User
from app.modules.users.service import UsersService


def get_minio_client() -> Minio:
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ROOT_USER,
        secret_key=settings.MINIO_ROOT_PASSWORD,
        secure=settings.MINIO_SECURE,
    )


class StorageService:
    def __init__(self, db):
        self.db = db
        self.repo = FileRepository(db)
        self.client = get_minio_client()

    def _meta_cache_key(self, file_id: uuid.UUID) -> str:
        return cache.key("files", file_id, "meta")

    def _cache_file_meta(self, file_record: FileRecord) -> None:
        cache.set(
            self._meta_cache_key(file_record.id),
            {
                "id": str(file_record.id),
                "user_id": str(file_record.user_id),
                "original_name": file_record.original_name,
                "object_key": file_record.object_key,
                "size": file_record.size,
                "mimetype": file_record.mimetype,
                "bucket": file_record.bucket,
                "created_at": file_record.created_at,
                "updated_at": file_record.updated_at,
                "deleted_at": file_record.deleted_at,
            },
            settings.FILE_META_CACHE_TTL_SECONDS,
        )

    def _file_from_cache(self, data: dict | None) -> FileRecord | None:
        if data is None:
            return None
        if data.get("deleted_at") is not None:
            return None
        return FileRecord(
            id=uuid.UUID(data["id"]),
            user_id=uuid.UUID(data["user_id"]),
            original_name=data["original_name"],
            object_key=data["object_key"],
            size=int(data["size"]),
            mimetype=data["mimetype"],
            bucket=data["bucket"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            deleted_at=data.get("deleted_at"),
        )

    def _invalidate_file_meta(self, file_id: uuid.UUID) -> None:
        cache.del_key(self._meta_cache_key(file_id))

    def _validate_upload(self, upload: UploadFile) -> tuple[str, int]:
        mimetype = (upload.content_type or "").lower()
        if mimetype not in settings.avatar_allowed_mime_types:
            raise AppException("Unsupported file type")

        size = getattr(upload, "size", None)
        if size is None:
            current_position = upload.file.tell()
            upload.file.seek(0, 2)
            size = upload.file.tell()
            upload.file.seek(current_position)

        if size <= 0:
            raise AppException("File is empty")
        if size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise AppException("File is too large")

        upload.file.seek(0)
        return mimetype, int(size)

    def _object_key(self, user_id: uuid.UUID, file_id: uuid.UUID, filename: str) -> str:
        suffix = Path(filename).suffix.lower()
        suffix = suffix if re.fullmatch(r"\.[a-z0-9]{1,10}", suffix) else ""
        return f"users/{user_id}/files/{file_id}{suffix}"

    def uploadFile(self, stream: BinaryIO, filename: str, mimetype: str, userId: uuid.UUID, size: int) -> FileRecord:
        file_id = uuid.uuid4()
        object_key = self._object_key(userId, file_id, filename)

        try:
            self.client.put_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=object_key,
                data=stream,
                length=size,
                content_type=mimetype,
            )
        except S3Error as exc:
            if exc.code == "NoSuchBucket":
                raise AppException("Storage bucket does not exist. Create it manually in MinIO Console")
            raise

        file_record = self.repo.create(
            {
                "id": file_id,
                "user_id": userId,
                "original_name": filename,
                "object_key": object_key,
                "size": size,
                "mimetype": mimetype,
                "bucket": settings.MINIO_BUCKET,
            }
        )
        self.db.commit()
        self._cache_file_meta(file_record)
        return file_record

    def upload_user_file(self, upload: UploadFile, current_user: User) -> FileRecord:
        mimetype, size = self._validate_upload(upload)
        return self.uploadFile(
            stream=upload.file,
            filename=upload.filename or "upload",
            mimetype=mimetype,
            userId=current_user.id,
            size=size,
        )

    def getFileStream(self, objectKey: str):
        return self.client.get_object(settings.MINIO_BUCKET, objectKey)

    def deleteFile(self, objectKey: str) -> None:
        try:
            self.client.remove_object(settings.MINIO_BUCKET, objectKey)
        except S3Error as exc:
            if exc.code != "NoSuchKey":
                raise

    def fileExists(self, objectKey: str) -> bool:
        try:
            self.client.stat_object(settings.MINIO_BUCKET, objectKey)
            return True
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchBucket"}:
                return False
            raise

    def get_owned_file(self, file_id: uuid.UUID, current_user: User) -> FileRecord:
        cached = self._file_from_cache(cache.get(self._meta_cache_key(file_id)))
        if cached is not None:
            if cached.user_id != current_user.id:
                raise ForbiddenException("You do not have access to this file")
            return cached

        file_record = self.repo.get_active_by_id(file_id)
        if file_record is None:
            raise NotFoundException("File not found")
        if file_record.user_id != current_user.id:
            raise ForbiddenException("You do not have access to this file")

        self._cache_file_meta(file_record)
        return file_record

    def delete_owned_file(self, file_id: uuid.UUID, current_user: User) -> None:
        file_record = self.get_owned_file(file_id, current_user)
        self.repo.soft_delete(file_record)
        self.db.collection("users").update_one(
            {
                "_id": str(current_user.id),
                "avatar_file_id": str(file_id),
            },
            {
                "$set": {
                    "avatar_file_id": None,
                }
            },
        )
        self.db.commit()
        self._invalidate_file_meta(file_id)
        cache.del_key(cache.key("users", "profile", current_user.id))
        self.deleteFile(file_record.object_key)

    def to_response(self, file_record: FileRecord) -> FileResponseDTO:
        return FileResponseDTO.model_validate(file_record)


class ProfileService:
    def __init__(self, db):
        self.db = db
        self.users = UsersService(db)
        self.files = StorageService(db)

    def get_profile(self, current_user: User) -> ProfileResponseDTO:
        user = self.users.get_active_by_id(current_user.id)
        if user is None:
            raise NotFoundException("User not found")
        return self._build_profile_response(user)

    def update_profile(self, payload: ProfileUpdateDTO, current_user: User) -> ProfileResponseDTO:
        update_data = payload.model_dump(exclude_unset=True)

        avatar_file_id = update_data.get("avatar_file_id")
        if "avatar_file_id" in update_data and avatar_file_id is not None:
            self.files.get_owned_file(avatar_file_id, current_user)

        updated = self.users.update_profile(current_user, update_data)
        return self._build_profile_response(updated)

    def _build_profile_response(self, user: User) -> ProfileResponseDTO:
        avatar = None
        if user.avatar_file_id is not None:
            file_record = self.files.repo.get_active_by_id_for_user(user.avatar_file_id, user.id)
            if file_record is not None:
                avatar = self.files.to_response(file_record)

        return ProfileResponseDTO(
            id=user.id,
            email=user.email,
            phone=user.phone,
            display_name=user.display_name,
            bio=user.bio,
            avatar_file_id=user.avatar_file_id,
            avatar=avatar,
            created_at=user.created_at,
        )
