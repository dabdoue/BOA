"""
BOA Job Routes
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from boa.db.models import JobStatus
from boa.db.job_queue import JobQueue
from boa.server.deps import get_db
from boa.server.schemas import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=List[JobResponse])
def list_jobs(
    campaign_id: UUID | None = None,
    status_filter: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> List[JobResponse]:
    """List jobs."""
    queue = JobQueue(db)
    
    status_enum = JobStatus(status_filter) if status_filter else None
    jobs = queue.list_jobs(
        campaign_id=campaign_id,
        status=status_enum,
        limit=limit,
        offset=offset,
    )
    
    return [JobResponse(
        id=j.id,
        campaign_id=j.campaign_id,
        job_type=j.job_type.value,
        status=j.status.value,
        params=j.params,
        result=j.result,
        error=j.error,
        progress=j.progress,
        created_at=j.created_at,
        started_at=j.started_at,
        completed_at=j.completed_at,
    ) for j in jobs]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> JobResponse:
    """Get job by ID."""
    queue = JobQueue(db)
    
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    
    return JobResponse(
        id=job.id,
        campaign_id=job.campaign_id,
        job_type=job.job_type.value,
        status=job.status.value,
        params=job.params,
        result=job.result,
        error=job.error,
        progress=job.progress,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.post("/{job_id}/cancel", response_model=JobResponse)
def cancel_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> JobResponse:
    """Cancel a pending job."""
    queue = JobQueue(db)
    
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    
    if job.status != JobStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in {job.status.value} status",
        )
    
    job = queue.cancel_job(job_id)
    db.commit()
    
    return JobResponse(
        id=job.id,
        campaign_id=job.campaign_id,
        job_type=job.job_type.value,
        status=job.status.value,
        params=job.params,
        result=job.result,
        error=job.error,
        progress=job.progress,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )





