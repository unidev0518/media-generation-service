"""Custom exceptions for the application."""

from typing import Any, Dict, Optional


class MediaGenerationException(Exception):
    """Base exception for media generation service."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        self.error_code = error_code
        super().__init__(self.message)


class JobNotFoundException(MediaGenerationException):
    """Exception raised when a job is not found."""

    def __init__(self, job_id: str) -> None:
        super().__init__(
            message=f"Job with ID {job_id} not found",
            details={"job_id": job_id},
            error_code="JOB_NOT_FOUND",
        )


class JobAlreadyExistsException(MediaGenerationException):
    """Exception raised when trying to create a job that already exists."""

    def __init__(self, job_id: str) -> None:
        super().__init__(
            message=f"Job with ID {job_id} already exists",
            details={"job_id": job_id},
            error_code="JOB_ALREADY_EXISTS",
        )


class ReplicateAPIException(MediaGenerationException):
    """Exception raised when Replicate API calls fail."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = {"status_code": status_code, "response_data": response_data}
        super().__init__(
            message=message,
            details=details,
            error_code="REPLICATE_API_ERROR",
        )


class StorageException(MediaGenerationException):
    """Exception raised when storage operations fail."""

    def __init__(self, message: str, operation: str, path: Optional[str] = None) -> None:
        details = {"operation": operation, "path": path}
        super().__init__(
            message=message,
            details=details,
            error_code="STORAGE_ERROR",
        )


class JobProcessingException(MediaGenerationException):
    """Exception raised when job processing fails."""

    def __init__(
        self,
        message: str,
        job_id: str,
        retry_count: int = 0,
        max_retries: int = 3,
    ) -> None:
        details = {
            "job_id": job_id,
            "retry_count": retry_count,
            "max_retries": max_retries,
        }
        super().__init__(
            message=message,
            details=details,
            error_code="JOB_PROCESSING_ERROR",
        )


class ValidationException(MediaGenerationException):
    """Exception raised when validation fails."""

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        details = {"field": field} if field else {}
        super().__init__(
            message=message,
            details=details,
            error_code="VALIDATION_ERROR",
        ) 