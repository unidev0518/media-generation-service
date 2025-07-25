"""Celery tasks for media generation."""

import asyncio
import uuid
from typing import Any, Dict

from celery import Task
from celery.exceptions import Retry
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.replicate_client import ReplicateClient
from app.clients.storage_client import StorageClient
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.exceptions import (
    JobNotFoundException,
    ReplicateAPIException,
    StorageException,
    JobProcessingException,
)
from app.models.job import Job, JobStatus
from app.repositories.job_repository import JobRepository
from app.tasks.celery_app import celery_app


class CallbackTask(Task):
    """Custom Celery task with callback support."""

    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict) -> None:
        """Called when task succeeds."""
        print(f"Task {task_id} succeeded with result: {retval}")

    def on_failure(
        self, 
        exc: Exception, 
        task_id: str, 
        args: tuple, 
        kwargs: dict, 
        einfo: Any
    ) -> None:
        """Called when task fails."""
        print(f"Task {task_id} failed with exception: {exc}")
        
        # Update job status in database
        if args:
            job_id = args[0]
            asyncio.run(self._mark_job_failed(job_id, str(exc)))

    async def _mark_job_failed(self, job_id: str, error_message: str) -> None:
        """Mark job as failed in database."""
        try:
            async with AsyncSessionLocal() as session:
                repository = JobRepository(session)
                job = await repository.get_by_id(uuid.UUID(job_id))
                job.mark_failed(error_message)
                await repository.update(job)
        except Exception as e:
            print(f"Failed to update job status: {e}")


@celery_app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(ReplicateAPIException, StorageException),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def generate_media_task(self: CallbackTask, job_id: str) -> Dict[str, Any]:
    """
    Generate media using Replicate API.
    
    Args:
        job_id: UUID string of the job to process
        
    Returns:
        Dictionary with task results
    """
    return asyncio.run(_generate_media_async(job_id, self))


async def _generate_media_async(job_id: str, task: CallbackTask) -> Dict[str, Any]:
    """Async implementation of media generation."""
    settings = get_settings()
    
    async with AsyncSessionLocal() as session:
        repository = JobRepository(session)
        
        try:
            # Get job from database
            job = await repository.get_by_id(uuid.UUID(job_id))
            
            if job.status != JobStatus.PENDING:
                raise JobProcessingException(
                    f"Job {job_id} is not in pending status: {job.status}",
                    job_id=job_id
                )

            # Mark job as processing
            job.mark_processing()
            await repository.update(job)

            # Initialize clients
            replicate_client = ReplicateClient()
            storage_client = StorageClient()

            # Prepare input for Replicate
            model_version = job.metadata.get("model", 
                "stability-ai/stable-diffusion:27b93a2413e7f36cd83da926f3656280b2931564ff050bf9575f1fdf9bcd7478"
            )
            
            input_data = {
                "prompt": job.prompt,
                **job.parameters
            }

            # Create prediction on Replicate
            await _update_job_progress(repository, job, 0.1, "Creating prediction...")
            
            prediction = await replicate_client.create_prediction(
                model=model_version,
                input_data=input_data
            )
            
            prediction_id = prediction["id"]
            job.replicate_prediction_id = prediction_id
            await repository.update(job)

            # Wait for completion with progress updates
            await _update_job_progress(repository, job, 0.2, "Processing...")
            
            completed_prediction = await _wait_for_prediction_with_progress(
                replicate_client, 
                repository,
                job,
                prediction_id
            )

            # Check if prediction succeeded
            if completed_prediction["status"] != "succeeded":
                error_msg = completed_prediction.get("error", "Unknown error")
                raise ReplicateAPIException(f"Prediction failed: {error_msg}")

            # Download generated media
            await _update_job_progress(repository, job, 0.9, "Downloading result...")
            
            output_urls = completed_prediction.get("output", [])
            if not output_urls:
                raise ReplicateAPIException("No output generated")

            # Download the first output (handle multiple outputs if needed)
            output_url = output_urls[0] if isinstance(output_urls, list) else output_urls
            media_data = await replicate_client.download_output(output_url)

            # Determine content type
            content_type = _determine_content_type(output_url)
            
            # Upload to storage
            await _update_job_progress(repository, job, 0.95, "Saving to storage...")
            
            storage_path, public_url = await storage_client.upload_file(
                job_id=job.id,
                file_data=media_data,
                content_type=content_type
            )

            # Mark job as completed
            job.mark_completed(
                result_url=public_url,
                result_path=storage_path,
                file_size=len(media_data),
                file_type=content_type
            )
            await repository.update(job)

            return {
                "job_id": job_id,
                "status": "completed",
                "result_url": public_url,
                "file_size": len(media_data),
                "prediction_id": prediction_id,
            }

        except (ReplicateAPIException, StorageException) as e:
            # These exceptions will trigger retry
            await _handle_retryable_error(repository, job, str(e), task)
            raise

        except Exception as e:
            # Mark job as failed for non-retryable errors
            await _handle_fatal_error(repository, job, str(e))
            raise JobProcessingException(
                f"Job processing failed: {str(e)}",
                job_id=job_id
            )


async def _wait_for_prediction_with_progress(
    client: ReplicateClient,
    repository: JobRepository,
    job: Job,
    prediction_id: str,
    max_wait_time: int = 300
) -> Dict[str, Any]:
    """Wait for prediction completion with progress updates."""
    import time
    
    start_time = time.time()
    last_progress_update = 0.2
    
    while time.time() - start_time < max_wait_time:
        prediction = await client.get_prediction(prediction_id)
        status = prediction.get("status")
        
        # Update progress based on elapsed time (rough estimation)
        elapsed = time.time() - start_time
        progress = min(0.2 + (elapsed / max_wait_time) * 0.7, 0.9)
        
        if progress > last_progress_update + 0.1:
            await _update_job_progress(repository, job, progress, f"Processing... ({status})")
            last_progress_update = progress
        
        if status in ("succeeded", "failed", "canceled"):
            return prediction
            
        await asyncio.sleep(2)
    
    raise ReplicateAPIException(
        f"Prediction {prediction_id} timed out after {max_wait_time} seconds"
    )


async def _update_job_progress(
    repository: JobRepository,
    job: Job,
    progress: float,
    message: str = ""
) -> None:
    """Update job progress."""
    job.progress = progress
    if message:
        job.metadata = {**job.metadata, "status_message": message}
    await repository.update(job)


async def _handle_retryable_error(
    repository: JobRepository,
    job: Job,
    error_message: str,
    task: CallbackTask
) -> None:
    """Handle retryable errors."""
    job.retry_count += 1
    job.error_message = error_message
    await repository.update(job)
    
    if job.retry_count >= job.max_retries:
        job.mark_failed(error_message, increment_retry=False)
        await repository.update(job)


async def _handle_fatal_error(
    repository: JobRepository,
    job: Job,
    error_message: str
) -> None:
    """Handle fatal errors that shouldn't be retried."""
    job.mark_failed(error_message, increment_retry=False)
    await repository.update(job)


def _determine_content_type(url: str) -> str:
    """Determine content type from URL."""
    url_lower = url.lower()
    
    if url_lower.endswith('.png'):
        return "image/png"
    elif url_lower.endswith(('.jpg', '.jpeg')):
        return "image/jpeg"
    elif url_lower.endswith('.gif'):
        return "image/gif"
    elif url_lower.endswith('.webp'):
        return "image/webp"
    elif url_lower.endswith('.mp4'):
        return "video/mp4"
    else:
        return "image/png"  # Default 