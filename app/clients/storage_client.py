"""Storage client for managing media files."""

import os
import uuid
from pathlib import Path
from typing import Optional, Tuple

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings
from app.core.exceptions import StorageException


class StorageClient:
    """Client for managing file storage (MinIO or local filesystem)."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.storage_type = self.settings.STORAGE_TYPE
        
        if self.storage_type == "minio":
            self._init_minio_client()
        else:
            self._init_local_storage()

    def _init_minio_client(self) -> None:
        """Initialize MinIO client."""
        try:
            self.minio_client = Minio(
                self.settings.MINIO_ENDPOINT,
                access_key=self.settings.MINIO_ACCESS_KEY,
                secret_key=self.settings.MINIO_SECRET_KEY,
                secure=self.settings.MINIO_SECURE,
            )
            
            # Ensure bucket exists
            if not self.minio_client.bucket_exists(self.settings.MINIO_BUCKET_NAME):
                self.minio_client.make_bucket(self.settings.MINIO_BUCKET_NAME)
                
        except S3Error as e:
            raise StorageException(
                f"Failed to initialize MinIO client: {str(e)}",
                operation="init",
            )

    def _init_local_storage(self) -> None:
        """Initialize local storage directory."""
        self.local_path = Path(self.settings.LOCAL_STORAGE_PATH)
        self.local_path.mkdir(parents=True, exist_ok=True)

    def _generate_file_path(self, job_id: uuid.UUID, file_extension: str = ".png") -> str:
        """Generate a unique file path for a job."""
        return f"{job_id}{file_extension}"

    async def upload_file(
        self, 
        job_id: uuid.UUID, 
        file_data: bytes, 
        content_type: str = "image/png"
    ) -> Tuple[str, str]:
        """
        Upload file to storage.
        
        Returns:
            Tuple of (storage_path, public_url)
        """
        file_extension = self._get_extension_from_content_type(content_type)
        file_path = self._generate_file_path(job_id, file_extension)
        
        if self.storage_type == "minio":
            return await self._upload_to_minio(file_path, file_data, content_type)
        else:
            return await self._upload_to_local(file_path, file_data)

    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Get file extension from content type."""
        extensions = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "video/mp4": ".mp4",
            "video/avi": ".avi",
        }
        return extensions.get(content_type, ".png")

    async def _upload_to_minio(
        self, 
        file_path: str, 
        file_data: bytes, 
        content_type: str
    ) -> Tuple[str, str]:
        """Upload file to MinIO."""
        try:
            # Upload file
            from io import BytesIO
            
            self.minio_client.put_object(
                self.settings.MINIO_BUCKET_NAME,
                file_path,
                BytesIO(file_data),
                length=len(file_data),
                content_type=content_type,
            )
            
            # Generate public URL
            if self.settings.MINIO_SECURE:
                protocol = "https"
            else:
                protocol = "http"
                
            public_url = f"{protocol}://{self.settings.MINIO_ENDPOINT}/{self.settings.MINIO_BUCKET_NAME}/{file_path}"
            
            return file_path, public_url
            
        except S3Error as e:
            raise StorageException(
                f"Failed to upload to MinIO: {str(e)}",
                operation="upload",
                path=file_path,
            )

    async def _upload_to_local(self, file_path: str, file_data: bytes) -> Tuple[str, str]:
        """Upload file to local filesystem."""
        try:
            full_path = self.local_path / file_path
            
            with open(full_path, "wb") as f:
                f.write(file_data)
                
            # Generate public URL (would need proper server setup)
            public_url = f"/media/{file_path}"
            
            return str(full_path), public_url
            
        except (OSError, IOError) as e:
            raise StorageException(
                f"Failed to upload to local storage: {str(e)}",
                operation="upload",
                path=file_path,
            )

    async def download_file(self, file_path: str) -> bytes:
        """Download file from storage."""
        if self.storage_type == "minio":
            return await self._download_from_minio(file_path)
        else:
            return await self._download_from_local(file_path)

    async def _download_from_minio(self, file_path: str) -> bytes:
        """Download file from MinIO."""
        try:
            response = self.minio_client.get_object(
                self.settings.MINIO_BUCKET_NAME, 
                file_path
            )
            return response.read()
            
        except S3Error as e:
            raise StorageException(
                f"Failed to download from MinIO: {str(e)}",
                operation="download",
                path=file_path,
            )

    async def _download_from_local(self, file_path: str) -> bytes:
        """Download file from local filesystem."""
        try:
            if os.path.isabs(file_path):
                full_path = Path(file_path)
            else:
                full_path = self.local_path / file_path
                
            with open(full_path, "rb") as f:
                return f.read()
                
        except (OSError, IOError) as e:
            raise StorageException(
                f"Failed to download from local storage: {str(e)}",
                operation="download",
                path=file_path,
            )

    async def delete_file(self, file_path: str) -> None:
        """Delete file from storage."""
        if self.storage_type == "minio":
            await self._delete_from_minio(file_path)
        else:
            await self._delete_from_local(file_path)

    async def _delete_from_minio(self, file_path: str) -> None:
        """Delete file from MinIO."""
        try:
            self.minio_client.remove_object(
                self.settings.MINIO_BUCKET_NAME, 
                file_path
            )
            
        except S3Error as e:
            raise StorageException(
                f"Failed to delete from MinIO: {str(e)}",
                operation="delete",
                path=file_path,
            )

    async def _delete_from_local(self, file_path: str) -> None:
        """Delete file from local filesystem."""
        try:
            if os.path.isabs(file_path):
                full_path = Path(file_path)
            else:
                full_path = self.local_path / file_path
                
            if full_path.exists():
                full_path.unlink()
                
        except (OSError, IOError) as e:
            raise StorageException(
                f"Failed to delete from local storage: {str(e)}",
                operation="delete",
                path=file_path,
            )

    async def file_exists(self, file_path: str) -> bool:
        """Check if file exists in storage."""
        if self.storage_type == "minio":
            return await self._file_exists_minio(file_path)
        else:
            return await self._file_exists_local(file_path)

    async def _file_exists_minio(self, file_path: str) -> bool:
        """Check if file exists in MinIO."""
        try:
            self.minio_client.stat_object(
                self.settings.MINIO_BUCKET_NAME, 
                file_path
            )
            return True
        except S3Error:
            return False

    async def _file_exists_local(self, file_path: str) -> bool:
        """Check if file exists in local filesystem."""
        if os.path.isabs(file_path):
            full_path = Path(file_path)
        else:
            full_path = self.local_path / file_path
        return full_path.exists() 