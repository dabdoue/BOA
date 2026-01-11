"""
BOA Job Queue

SQLite-backed async job queue for long-running operations.
Supports enqueue, dequeue, status updates, and cancellation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlmodel import Session, select, col

from boa.db.models import Job, JobStatus, JobType


class JobQueueError(Exception):
    """Base exception for job queue errors."""
    pass


class JobNotFoundError(JobQueueError):
    """Job not found."""
    pass


class JobAlreadyRunningError(JobQueueError):
    """Job is already running."""
    pass


class JobQueue:
    """
    SQLite-backed job queue for async operations.
    
    Provides FIFO queue semantics with status tracking.
    Thread-safe through database transactions.
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def enqueue(
        self,
        job_type: JobType,
        params: dict[str, Any],
        campaign_id: UUID | None = None,
    ) -> Job:
        """
        Add a new job to the queue.
        
        Args:
            job_type: Type of job
            params: Job parameters
            campaign_id: Optional associated campaign
            
        Returns:
            Created Job entity
        """
        job = Job(
            job_type=job_type,
            params=params,
            campaign_id=campaign_id,
            status=JobStatus.PENDING,
        )
        self.session.add(job)
        self.session.flush()
        self.session.refresh(job)
        return job
    
    def dequeue(self) -> Job | None:
        """
        Get the next pending job and mark it as running.
        
        Returns:
            Next pending job, or None if queue is empty
        """
        # Get oldest pending job
        stmt = select(Job).where(Job.status == JobStatus.PENDING)
        stmt = stmt.order_by(col(Job.created_at).asc())
        stmt = stmt.limit(1)
        
        job = self.session.exec(stmt).first()
        
        if job:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            self.session.add(job)
            self.session.flush()
            self.session.refresh(job)
        
        return job
    
    def get(self, job_id: UUID) -> Job | None:
        """Get job by ID."""
        return self.session.get(Job, job_id)
    
    def get_or_raise(self, job_id: UUID) -> Job:
        """Get job by ID or raise error."""
        job = self.get(job_id)
        if not job:
            raise JobNotFoundError(f"Job {job_id} not found")
        return job
    
    def complete(
        self,
        job_id: UUID,
        result: dict[str, Any] | None = None,
    ) -> Job:
        """
        Mark job as completed.
        
        Args:
            job_id: Job to complete
            result: Optional result data
            
        Returns:
            Updated job
        """
        job = self.get_or_raise(job_id)
        job.status = JobStatus.COMPLETED
        job.result = result
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        job.progress = 1.0
        self.session.add(job)
        self.session.flush()
        self.session.refresh(job)
        return job
    
    def fail(
        self,
        job_id: UUID,
        error: str,
    ) -> Job:
        """
        Mark job as failed.
        
        Args:
            job_id: Job that failed
            error: Error message
            
        Returns:
            Updated job
        """
        job = self.get_or_raise(job_id)
        job.status = JobStatus.FAILED
        job.error = error
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        self.session.add(job)
        self.session.flush()
        self.session.refresh(job)
        return job
    
    def cancel(self, job_id: UUID) -> Job:
        """
        Cancel a pending job.
        
        Args:
            job_id: Job to cancel
            
        Returns:
            Updated job
            
        Raises:
            JobAlreadyRunningError: If job is already running
        """
        job = self.get_or_raise(job_id)
        
        if job.status == JobStatus.RUNNING:
            raise JobAlreadyRunningError(
                f"Job {job_id} is already running and cannot be cancelled"
            )
        
        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            # Already terminal state
            return job
        
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        self.session.add(job)
        self.session.flush()
        self.session.refresh(job)
        return job
    
    def update_progress(
        self,
        job_id: UUID,
        progress: float,
    ) -> Job:
        """
        Update job progress.
        
        Args:
            job_id: Job to update
            progress: Progress value 0-1
            
        Returns:
            Updated job
        """
        job = self.get_or_raise(job_id)
        job.progress = max(0.0, min(1.0, progress))
        job.updated_at = datetime.utcnow()
        self.session.add(job)
        self.session.flush()
        self.session.refresh(job)
        return job
    
    def list(
        self,
        campaign_id: UUID | None = None,
        status: JobStatus | None = None,
        job_type: JobType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Job]:
        """
        List jobs with optional filters.
        
        Args:
            campaign_id: Filter by campaign
            status: Filter by status
            job_type: Filter by type
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of matching jobs
        """
        stmt = select(Job)
        
        if campaign_id is not None:
            stmt = stmt.where(Job.campaign_id == campaign_id)
        if status is not None:
            stmt = stmt.where(Job.status == status)
        if job_type is not None:
            stmt = stmt.where(Job.job_type == job_type)
        
        stmt = stmt.order_by(col(Job.created_at).desc())
        stmt = stmt.offset(offset).limit(limit)
        
        return list(self.session.exec(stmt).all())
    
    def pending_count(self, campaign_id: UUID | None = None) -> int:
        """Count pending jobs."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(Job).where(
            Job.status == JobStatus.PENDING
        )
        if campaign_id:
            stmt = stmt.where(Job.campaign_id == campaign_id)
        return self.session.exec(stmt).one()
    
    def running_count(self, campaign_id: UUID | None = None) -> int:
        """Count running jobs."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(Job).where(
            Job.status == JobStatus.RUNNING
        )
        if campaign_id:
            stmt = stmt.where(Job.campaign_id == campaign_id)
        return self.session.exec(stmt).one()
    
    def cleanup_stale(self, max_age_hours: int = 24) -> int:
        """
        Mark old running jobs as failed (crashed workers).
        
        Args:
            max_age_hours: Max hours a job can be running
            
        Returns:
            Number of jobs marked as failed
        """
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        stmt = select(Job).where(
            Job.status == JobStatus.RUNNING,
            Job.started_at < cutoff,
        )
        stale_jobs = list(self.session.exec(stmt).all())
        
        for job in stale_jobs:
            job.status = JobStatus.FAILED
            job.error = f"Job timed out after {max_age_hours} hours"
            job.completed_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            self.session.add(job)
        
        self.session.flush()
        return len(stale_jobs)
    
    def cleanup_completed(self, keep_last: int = 1000) -> int:
        """
        Remove old completed/failed jobs.
        
        Args:
            keep_last: Number of recent jobs to keep
            
        Returns:
            Number of jobs removed
        """
        # Get IDs of jobs to keep
        stmt = select(Job.id).where(
            Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED])
        )
        stmt = stmt.order_by(col(Job.completed_at).desc())
        stmt = stmt.limit(keep_last)
        
        keep_ids = set(self.session.exec(stmt).all())
        
        # Find jobs to delete
        stmt = select(Job).where(
            Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]),
            ~Job.id.in_(keep_ids),  # type: ignore
        )
        to_delete = list(self.session.exec(stmt).all())
        
        for job in to_delete:
            self.session.delete(job)
        
        self.session.flush()
        return len(to_delete)






