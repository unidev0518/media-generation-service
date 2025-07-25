"""Media generation API endpoints."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import get_job_service
from app.core.exceptions import (
    JobNotFoundException,
    ValidationException,
    MediaGenerationException,
)
from app.models.job import JobStatus
from app.schemas.generation import GenerationRequest, GenerationResponse
from app.schemas.job import JobResponse, JobStatusResponse
from app.services.job_service import JobService

router = APIRouter()


@router.post(
    "/generate",
    response_model=GenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create media generation job",
    description="Submit a prompt and parameters to generate media asynchronously",
)
async def create_generation_job(
    request: GenerationRequest,
    job_service: JobService = Depends(get_job_service),
) -> GenerationResponse:
    """Create a new media generation job."""
    try:
        job = await job_service.create_generation_job(request)
        
        return GenerationResponse(
            job_id=job.id,
            status=job.status.value,
            message="Job created successfully",
            estimated_time=60,  # Rough estimate in seconds
        )
        
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Validation failed",
                "message": e.message,
                "field": e.details.get("field"),
            },
        )
    except MediaGenerationException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": e.error_code,
                "message": e.message,
                "details": e.details,
            },
        )


@router.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status",
    description="Get the current status and progress of a generation job",
)
async def get_job_status(
    job_id: uuid.UUID,
    job_service: JobService = Depends(get_job_service),
) -> JobStatusResponse:
    """Get job status by ID."""
    try:
        job = await job_service.get_job_status(job_id)
        
        return JobStatusResponse(
            job_id=job.id,
            status=job.status,
            progress=job.progress,
            result_url=job.result_url,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        
    except JobNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Job not found",
                "message": f"Job with ID {job_id} does not exist",
            },
        )
    except MediaGenerationException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": e.error_code,
                "message": e.message,
                "details": e.details,
            },
        )


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get detailed job information",
    description="Get comprehensive details about a specific job",
)
async def get_job_details(
    job_id: uuid.UUID,
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """Get detailed job information."""
    try:
        job = await job_service.get_job_status(job_id)
        
        return JobResponse(
            job_id=job.id,
            prompt=job.prompt,
            parameters=job.parameters,
            status=job.status,
            progress=job.progress,
            result_url=job.result_url,
            file_size=job.file_size,
            file_type=job.file_type,
            error_message=job.error_message,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
            metadata=job.metadata,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
        
    except JobNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Job not found",
                "message": f"Job with ID {job_id} does not exist",
            },
        )


@router.get(
    "/jobs",
    response_model=List[JobResponse],
    summary="List jobs",
    description="Get a paginated list of jobs with optional status filtering",
)
async def list_jobs(
    limit: int = Query(default=10, ge=1, le=100, description="Number of jobs to return"),
    offset: int = Query(default=0, ge=0, description="Number of jobs to skip"),
    status: Optional[JobStatus] = Query(default=None, description="Filter by job status"),
    job_service: JobService = Depends(get_job_service),
) -> List[JobResponse]:
    """List jobs with pagination."""
    try:
        jobs = await job_service.get_job_list(
            limit=limit,
            offset=offset,
            status=status,
        )
        
        return [
            JobResponse(
                job_id=job.id,
                prompt=job.prompt,
                parameters=job.parameters,
                status=job.status,
                progress=job.progress,
                result_url=job.result_url,
                file_size=job.file_size,
                file_type=job.file_type,
                error_message=job.error_message,
                retry_count=job.retry_count,
                max_retries=job.max_retries,
                metadata=job.metadata,
                created_at=job.created_at,
                updated_at=job.updated_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
            )
            for job in jobs
        ]
        
    except MediaGenerationException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": e.error_code,
                "message": e.message,
                "details": e.details,
            },
        )


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=JobStatusResponse,
    summary="Cancel job",
    description="Cancel a running or pending job",
)
async def cancel_job(
    job_id: uuid.UUID,
    job_service: JobService = Depends(get_job_service),
) -> JobStatusResponse:
    """Cancel a job."""
    try:
        job = await job_service.cancel_job(job_id)
        
        return JobStatusResponse(
            job_id=job.id,
            status=job.status,
            progress=job.progress,
            result_url=job.result_url,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        
    except JobNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Job not found",
                "message": f"Job with ID {job_id} does not exist",
            },
        )
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Cannot cancel job",
                "message": e.message,
                "field": e.details.get("field"),
            },
        )


@router.post(
    "/jobs/{job_id}/retry",
    response_model=JobStatusResponse,
    summary="Retry failed job",
    description="Retry a failed job if it hasn't exceeded maximum retry attempts",
)
async def retry_job(
    job_id: uuid.UUID,
    job_service: JobService = Depends(get_job_service),
) -> JobStatusResponse:
    """Retry a failed job."""
    try:
        job = await job_service.retry_job(job_id)
        
        return JobStatusResponse(
            job_id=job.id,
            status=job.status,
            progress=job.progress,
            result_url=job.result_url,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        
    except JobNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Job not found",
                "message": f"Job with ID {job_id} does not exist",
            },
        )
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Cannot retry job",
                "message": e.message,
                "field": e.details.get("field"),
            },
        )


@router.get(
    "/stats",
    summary="Get statistics",
    description="Get job statistics and system health information",
)
async def get_statistics(
    job_service: JobService = Depends(get_job_service),
) -> dict:
    """Get job statistics."""
    try:
        stats = await job_service.get_job_statistics()
        return {
            "status": "healthy",
            "statistics": stats,
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": f"Failed to get statistics: {str(e)}",
            },
        ) 