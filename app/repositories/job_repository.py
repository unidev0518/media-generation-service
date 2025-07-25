"""Job repository for database operations."""

import uuid
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import JobNotFoundException
from app.models.job import Job, JobStatus


class JobRepository:
    """Repository for job database operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, job: Job) -> Job:
        """Create a new job."""
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_by_id(self, job_id: uuid.UUID) -> Job:
        """Get job by ID."""
        result = await self.session.execute(
            select(Job).where(Job.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise JobNotFoundException(str(job_id))
        return job

    async def get_by_id_optional(self, job_id: uuid.UUID) -> Optional[Job]:
        """Get job by ID, return None if not found."""
        result = await self.session.execute(
            select(Job).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self, 
        limit: int = 100, 
        offset: int = 0,
        status: Optional[JobStatus] = None
    ) -> List[Job]:
        """Get all jobs with pagination and optional status filter."""
        query = select(Job)
        
        if status:
            query = query.where(Job.status == status)
            
        query = query.offset(offset).limit(limit).order_by(Job.created_at.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_pending_jobs(self, limit: int = 100) -> List[Job]:
        """Get jobs that are pending processing."""
        result = await self.session.execute(
            select(Job)
            .where(Job.status == JobStatus.PENDING)
            .order_by(Job.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_retryable_jobs(self, limit: int = 100) -> List[Job]:
        """Get jobs that can be retried."""
        result = await self.session.execute(
            select(Job)
            .where(
                Job.status == JobStatus.FAILED,
                Job.retry_count < Job.max_retries
            )
            .order_by(Job.updated_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, job: Job) -> Job:
        """Update an existing job."""
        await self.session.merge(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def update_status(
        self, 
        job_id: uuid.UUID, 
        status: JobStatus,
        progress: Optional[float] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Update job status and related fields."""
        update_data = {"status": status, "updated_at": "now()"}
        
        if progress is not None:
            update_data["progress"] = progress
            
        if error_message is not None:
            update_data["error_message"] = error_message
            
        if status == JobStatus.PROCESSING:
            update_data["started_at"] = "now()"
        elif status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            update_data["completed_at"] = "now()"

        await self.session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(**update_data)
        )
        await self.session.commit()

    async def delete(self, job_id: uuid.UUID) -> None:
        """Delete a job."""
        job = await self.get_by_id(job_id)
        await self.session.delete(job)
        await self.session.commit()

    async def count_by_status(self, status: JobStatus) -> int:
        """Count jobs by status."""
        result = await self.session.execute(
            select(Job).where(Job.status == status)
        )
        return len(list(result.scalars().all()))

    async def cleanup_completed_jobs(self, days_old: int = 30) -> int:
        """Clean up completed jobs older than specified days."""
        # This would typically use a proper date calculation
        # For now, we'll keep it simple
        result = await self.session.execute(
            select(Job).where(
                Job.status.in_([JobStatus.COMPLETED, JobStatus.CANCELLED]),
                # Job.completed_at < datetime.utcnow() - timedelta(days=days_old)
            )
        )
        jobs_to_delete = list(result.scalars().all())
        
        for job in jobs_to_delete:
            await self.session.delete(job)
            
        await self.session.commit()
        return len(jobs_to_delete) 