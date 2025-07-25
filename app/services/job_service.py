"""Job service for business logic."""

import uuid
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import JobNotFoundException, ValidationException
from app.models.job import Job, JobStatus
from app.repositories.job_repository import JobRepository
from app.schemas.generation import GenerationRequest
from app.tasks.generation_tasks import generate_media_task


class JobService:
    """Service for job-related business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = JobRepository(session)
        self.settings = get_settings()

    async def create_generation_job(
        self, 
        request: GenerationRequest
    ) -> Job:
        """Create a new media generation job."""
        # Validate the request
        await self._validate_generation_request(request)

        # Create job instance
        job = Job(
            prompt=request.prompt,
            parameters=request.parameters,
            status=JobStatus.PENDING,
            max_retries=self.settings.MAX_RETRY_ATTEMPTS,
            metadata={
                "model": request.model,
                "request_timestamp": "now()",
            }
        )

        # Save to database
        job = await self.repository.create(job)

        # Enqueue background task
        task = generate_media_task.delay(str(job.id))
        
        # Update job with task ID
        job.celery_task_id = task.id
        await self.repository.update(job)

        return job

    async def get_job_status(self, job_id: uuid.UUID) -> Job:
        """Get job status and details."""
        return await self.repository.get_by_id(job_id)

    async def get_job_list(
        self, 
        limit: int = 100, 
        offset: int = 0,
        status: Optional[JobStatus] = None
    ) -> list[Job]:
        """Get list of jobs with pagination."""
        return await self.repository.get_all(
            limit=min(limit, 1000),  # Cap at 1000
            offset=max(offset, 0),   # Ensure non-negative
            status=status
        )

    async def cancel_job(self, job_id: uuid.UUID) -> Job:
        """Cancel a running job."""
        job = await self.repository.get_by_id(job_id)
        
        if job.is_terminal_status():
            raise ValidationException(
                f"Cannot cancel job in {job.status} status",
                field="status"
            )

        # Cancel Celery task if it exists
        if job.celery_task_id:
            from app.tasks.celery_app import celery_app
            celery_app.control.revoke(job.celery_task_id, terminate=True)

        # Update job status
        job.mark_cancelled()
        return await self.repository.update(job)

    async def retry_job(self, job_id: uuid.UUID) -> Job:
        """Retry a failed job."""
        job = await self.repository.get_by_id(job_id)
        
        if not job.can_retry():
            raise ValidationException(
                f"Job cannot be retried. Status: {job.status}, "
                f"Retries: {job.retry_count}/{job.max_retries}",
                field="retry"
            )

        # Reset job for retry
        job.status = JobStatus.PENDING
        job.error_message = None
        job.progress = 0.0
        job.started_at = None
        job.completed_at = None

        # Save updated job
        job = await self.repository.update(job)

        # Enqueue new task
        task = generate_media_task.delay(str(job.id))
        job.celery_task_id = task.id
        
        return await self.repository.update(job)

    async def update_job_progress(
        self, 
        job_id: uuid.UUID, 
        progress: float,
        status: Optional[JobStatus] = None
    ) -> None:
        """Update job progress."""
        if not 0.0 <= progress <= 1.0:
            raise ValidationException(
                "Progress must be between 0.0 and 1.0",
                field="progress"
            )

        job = await self.repository.get_by_id(job_id)
        job.progress = progress
        
        if status:
            job.status = status
            
        await self.repository.update(job)

    async def mark_job_processing(self, job_id: uuid.UUID) -> Job:
        """Mark job as processing."""
        job = await self.repository.get_by_id(job_id)
        job.mark_processing()
        return await self.repository.update(job)

    async def mark_job_completed(
        self, 
        job_id: uuid.UUID,
        result_url: str,
        result_path: str,
        file_size: Optional[int] = None,
        file_type: Optional[str] = None
    ) -> Job:
        """Mark job as completed with results."""
        job = await self.repository.get_by_id(job_id)
        job.mark_completed(
            result_url=result_url,
            result_path=result_path,
            file_size=file_size,
            file_type=file_type
        )
        return await self.repository.update(job)

    async def mark_job_failed(
        self, 
        job_id: uuid.UUID, 
        error_message: str,
        increment_retry: bool = True
    ) -> Job:
        """Mark job as failed."""
        job = await self.repository.get_by_id(job_id)
        job.mark_failed(error_message, increment_retry)
        return await self.repository.update(job)

    async def get_job_statistics(self) -> Dict[str, Any]:
        """Get job statistics."""
        stats = {}
        
        for status in JobStatus:
            count = await self.repository.count_by_status(status)
            stats[status.value] = count
            
        return {
            "job_counts": stats,
            "total_jobs": sum(stats.values()),
        }

    async def cleanup_old_jobs(self, days_old: int = 30) -> int:
        """Clean up old completed jobs."""
        return await self.repository.cleanup_completed_jobs(days_old)

    async def _validate_generation_request(self, request: GenerationRequest) -> None:
        """Validate generation request."""
        # Additional business logic validation can go here
        if not request.prompt.strip():
            raise ValidationException(
                "Prompt cannot be empty",
                field="prompt"
            )
            
        # Validate model format (basic check)
        if request.model and "/" not in request.model:
            raise ValidationException(
                "Model must be in format 'owner/model:version'",
                field="model"
            )
            
        # Validate parameters
        if request.parameters:
            await self._validate_generation_parameters(request.parameters)

    async def _validate_generation_parameters(self, parameters: Dict[str, Any]) -> None:
        """Validate generation parameters."""
        # Image dimension validation
        if "width" in parameters:
            width = parameters["width"]
            if not isinstance(width, int) or width < 64 or width > 2048:
                raise ValidationException(
                    "Width must be an integer between 64 and 2048",
                    field="parameters.width"
                )
                
        if "height" in parameters:
            height = parameters["height"]
            if not isinstance(height, int) or height < 64 or height > 2048:
                raise ValidationException(
                    "Height must be an integer between 64 and 2048",
                    field="parameters.height"
                )
                
        # Inference steps validation
        if "num_inference_steps" in parameters:
            steps = parameters["num_inference_steps"]
            if not isinstance(steps, int) or steps < 1 or steps > 150:
                raise ValidationException(
                    "num_inference_steps must be an integer between 1 and 150",
                    field="parameters.num_inference_steps"
                )
                
        # Guidance scale validation
        if "guidance_scale" in parameters:
            scale = parameters["guidance_scale"]
            if not isinstance(scale, (int, float)) or scale < 0 or scale > 20:
                raise ValidationException(
                    "guidance_scale must be a number between 0 and 20",
                    field="parameters.guidance_scale"
                ) 