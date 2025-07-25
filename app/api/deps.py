"""FastAPI dependencies for dependency injection."""

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.services.job_service import JobService


async def get_job_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[JobService, None]:
    """Get job service dependency."""
    yield JobService(session) 