"""Job model for database persistence."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlmodel import Field, SQLModel


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(SQLModel, table=True):
    """Job model for storing generation job metadata."""

    __tablename__ = "jobs"

    # Primary key
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )

    # Job details
    prompt: str = Field(description="Generation prompt")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Generation parameters",
    )

    # Status tracking
    status: JobStatus = Field(
        default=JobStatus.PENDING, description="Current job status"
    )
    progress: float = Field(default=0.0, description="Job progress (0.0 to 1.0)")

    # Results
    result_url: Optional[str] = Field(default=None, description="URL to result file")
    result_path: Optional[str] = Field(
        default=None, description="Storage path to result file"
    )
    file_size: Optional[int] = Field(default=None, description="Result file size in bytes")
    file_type: Optional[str] = Field(default=None, description="Result file MIME type")

    # Error handling
    error_message: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Error message if job failed",
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts")

    # External references
    replicate_prediction_id: Optional[str] = Field(
        default=None, description="Replicate prediction ID"
    )
    celery_task_id: Optional[str] = Field(
        default=None, description="Celery task ID"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Additional metadata",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow),
        description="Job creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
        description="Job last update timestamp",
    )
    started_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime),
        description="Job start timestamp",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime),
        description="Job completion timestamp",
    )

    def is_terminal_status(self) -> bool:
        """Check if job is in a terminal status."""
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)

    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return (
            self.status == JobStatus.FAILED
            and self.retry_count < self.max_retries
        )

    def mark_processing(self) -> None:
        """Mark job as processing."""
        self.status = JobStatus.PROCESSING
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_completed(
        self,
        result_url: str,
        result_path: str,
        file_size: Optional[int] = None,
        file_type: Optional[str] = None,
    ) -> None:
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED
        self.result_url = result_url
        self.result_path = result_path
        self.file_size = file_size
        self.file_type = file_type
        self.progress = 1.0
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error_message: str, increment_retry: bool = True) -> None:
        """Mark job as failed."""
        self.status = JobStatus.FAILED
        self.error_message = error_message
        if increment_retry:
            self.retry_count += 1
        self.updated_at = datetime.utcnow()

    def mark_cancelled(self) -> None:
        """Mark job as cancelled."""
        self.status = JobStatus.CANCELLED
        self.updated_at = datetime.utcnow() 