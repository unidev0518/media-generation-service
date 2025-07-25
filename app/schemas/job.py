"""Pydantic schemas for job endpoints."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.models.job import JobStatus


class JobStatusResponse(BaseModel):
    """Response schema for job status endpoint."""

    job_id: uuid.UUID = Field(
        description="Unique job identifier"
    )
    
    status: JobStatus = Field(
        description="Current job status"
    )
    
    progress: float = Field(
        description="Job progress (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )
    
    result_url: Optional[str] = Field(
        default=None,
        description="URL to download the generated media (available when completed)"
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if job failed"
    )
    
    created_at: datetime = Field(
        description="Job creation timestamp"
    )
    
    updated_at: datetime = Field(
        description="Job last update timestamp"
    )
    
    estimated_completion: Optional[datetime] = Field(
        default=None,
        description="Estimated completion time"
    )

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            uuid.UUID: str
        }
        schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "processing",
                "progress": 0.65,
                "result_url": None,
                "error_message": None,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:31:30Z",
                "estimated_completion": "2024-01-15T10:32:00Z"
            }
        }


class JobResponse(BaseModel):
    """Detailed response schema for job information."""

    job_id: uuid.UUID = Field(
        description="Unique job identifier"
    )
    
    prompt: str = Field(
        description="Generation prompt"
    )
    
    parameters: Dict[str, Any] = Field(
        description="Generation parameters"
    )
    
    status: JobStatus = Field(
        description="Current job status"
    )
    
    progress: float = Field(
        description="Job progress (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )
    
    result_url: Optional[str] = Field(
        default=None,
        description="URL to download the generated media"
    )
    
    file_size: Optional[int] = Field(
        default=None,
        description="Result file size in bytes"
    )
    
    file_type: Optional[str] = Field(
        default=None,
        description="Result file MIME type"
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if job failed"
    )
    
    retry_count: int = Field(
        description="Number of retry attempts"
    )
    
    max_retries: int = Field(
        description="Maximum retry attempts"
    )
    
    metadata: Dict[str, Any] = Field(
        description="Additional metadata"
    )
    
    created_at: datetime = Field(
        description="Job creation timestamp"
    )
    
    updated_at: datetime = Field(
        description="Job last update timestamp"
    )
    
    started_at: Optional[datetime] = Field(
        default=None,
        description="Job start timestamp"
    )
    
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Job completion timestamp"
    )

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            uuid.UUID: str
        }
        schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "prompt": "A beautiful sunset over the ocean",
                "parameters": {
                    "width": 512,
                    "height": 512,
                    "num_inference_steps": 50
                },
                "status": "completed",
                "progress": 1.0,
                "result_url": "https://storage.example.com/media-files/123e4567-e89b-12d3-a456-426614174000.png",
                "file_size": 1024000,
                "file_type": "image/png",
                "error_message": None,
                "retry_count": 0,
                "max_retries": 3,
                "metadata": {},
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:32:00Z",
                "started_at": "2024-01-15T10:30:30Z",
                "completed_at": "2024-01-15T10:32:00Z"
            }
        } 