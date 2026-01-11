"""
Tests for BOA job queue.

Tests job lifecycle, queue operations, and cleanup.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4
import time

import pytest
from sqlmodel import Session

from boa.db.models import Campaign, JobStatus, JobType
from boa.db.job_queue import (
    JobQueue,
    JobNotFoundError,
    JobAlreadyRunningError,
)


class TestJobQueueEnqueue:
    """Tests for job enqueue operations."""
    
    def test_enqueue_basic(self, session: Session) -> None:
        """Test basic job enqueue."""
        queue = JobQueue(session)
        
        job = queue.enqueue(
            job_type=JobType.PROPOSE,
            params={"batch_size": 5},
        )
        
        assert job.id is not None
        assert job.job_type == JobType.PROPOSE
        assert job.status == JobStatus.PENDING
        assert job.params["batch_size"] == 5
        assert job.campaign_id is None
    
    def test_enqueue_with_campaign(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test enqueue with campaign association."""
        queue = JobQueue(session)
        
        job = queue.enqueue(
            job_type=JobType.PROPOSE,
            params={"strategies": ["default"]},
            campaign_id=sample_campaign.id,
        )
        
        assert job.campaign_id == sample_campaign.id
    
    def test_enqueue_different_types(self, session: Session) -> None:
        """Test enqueuing different job types."""
        queue = JobQueue(session)
        
        propose = queue.enqueue(JobType.PROPOSE, {"batch_size": 5})
        benchmark = queue.enqueue(JobType.BENCHMARK, {"suite": "dtlz"})
        export = queue.enqueue(JobType.EXPORT, {"format": "zip"})
        import_job = queue.enqueue(JobType.IMPORT, {"path": "bundle.zip"})
        
        assert propose.job_type == JobType.PROPOSE
        assert benchmark.job_type == JobType.BENCHMARK
        assert export.job_type == JobType.EXPORT
        assert import_job.job_type == JobType.IMPORT


class TestJobQueueDequeue:
    """Tests for job dequeue operations."""
    
    def test_dequeue_empty_queue(self, session: Session) -> None:
        """Test dequeue from empty queue."""
        queue = JobQueue(session)
        
        job = queue.dequeue()
        assert job is None
    
    def test_dequeue_fifo_order(self, session: Session) -> None:
        """Test FIFO ordering of dequeue."""
        queue = JobQueue(session)
        
        # Enqueue multiple jobs
        job1 = queue.enqueue(JobType.PROPOSE, {"order": 1})
        job2 = queue.enqueue(JobType.PROPOSE, {"order": 2})
        job3 = queue.enqueue(JobType.PROPOSE, {"order": 3})
        
        # Dequeue should return oldest first
        dequeued = queue.dequeue()
        assert dequeued is not None
        assert dequeued.id == job1.id
        assert dequeued.params["order"] == 1
    
    def test_dequeue_marks_running(self, session: Session) -> None:
        """Test that dequeue marks job as running."""
        queue = JobQueue(session)
        
        job = queue.enqueue(JobType.PROPOSE, {})
        dequeued = queue.dequeue()
        
        assert dequeued is not None
        assert dequeued.status == JobStatus.RUNNING
        assert dequeued.started_at is not None
    
    def test_dequeue_skips_running_jobs(self, session: Session) -> None:
        """Test that dequeue skips already running jobs."""
        queue = JobQueue(session)
        
        job1 = queue.enqueue(JobType.PROPOSE, {"order": 1})
        job2 = queue.enqueue(JobType.PROPOSE, {"order": 2})
        
        # First dequeue
        queue.dequeue()
        
        # Second dequeue should get job2
        dequeued = queue.dequeue()
        assert dequeued is not None
        assert dequeued.id == job2.id


class TestJobQueueCompletion:
    """Tests for job completion operations."""
    
    def test_complete_job(self, session: Session) -> None:
        """Test completing a job."""
        queue = JobQueue(session)
        
        job = queue.enqueue(JobType.PROPOSE, {})
        queue.dequeue()  # Start job
        
        completed = queue.complete(
            job.id,
            result={"iteration_id": str(uuid4())},
        )
        
        assert completed.status == JobStatus.COMPLETED
        assert completed.completed_at is not None
        assert completed.progress == 1.0
        assert completed.result is not None
    
    def test_fail_job(self, session: Session) -> None:
        """Test failing a job."""
        queue = JobQueue(session)
        
        job = queue.enqueue(JobType.PROPOSE, {})
        queue.dequeue()  # Start job
        
        failed = queue.fail(job.id, "Something went wrong")
        
        assert failed.status == JobStatus.FAILED
        assert failed.error == "Something went wrong"
        assert failed.completed_at is not None
    
    def test_complete_not_found(self, session: Session) -> None:
        """Test completing non-existent job."""
        queue = JobQueue(session)
        
        with pytest.raises(JobNotFoundError):
            queue.complete(uuid4(), {})


class TestJobQueueCancellation:
    """Tests for job cancellation."""
    
    def test_cancel_pending_job(self, session: Session) -> None:
        """Test cancelling a pending job."""
        queue = JobQueue(session)
        
        job = queue.enqueue(JobType.PROPOSE, {})
        cancelled = queue.cancel(job.id)
        
        assert cancelled.status == JobStatus.CANCELLED
        assert cancelled.completed_at is not None
    
    def test_cancel_running_job_fails(self, session: Session) -> None:
        """Test that running jobs cannot be cancelled."""
        queue = JobQueue(session)
        
        job = queue.enqueue(JobType.PROPOSE, {})
        queue.dequeue()  # Start job
        
        with pytest.raises(JobAlreadyRunningError):
            queue.cancel(job.id)
    
    def test_cancel_completed_job_noop(self, session: Session) -> None:
        """Test that cancelling completed job is a no-op."""
        queue = JobQueue(session)
        
        job = queue.enqueue(JobType.PROPOSE, {})
        queue.dequeue()
        queue.complete(job.id, {})
        
        # Should not raise, just return
        result = queue.cancel(job.id)
        assert result.status == JobStatus.COMPLETED


class TestJobQueueProgress:
    """Tests for job progress updates."""
    
    def test_update_progress(self, session: Session) -> None:
        """Test updating job progress."""
        queue = JobQueue(session)
        
        job = queue.enqueue(JobType.PROPOSE, {})
        queue.dequeue()
        
        updated = queue.update_progress(job.id, 0.5)
        assert updated.progress == 0.5
        
        updated = queue.update_progress(job.id, 0.75)
        assert updated.progress == 0.75
    
    def test_progress_clamped(self, session: Session) -> None:
        """Test that progress is clamped to 0-1."""
        queue = JobQueue(session)
        
        job = queue.enqueue(JobType.PROPOSE, {})
        
        updated = queue.update_progress(job.id, -0.5)
        assert updated.progress == 0.0
        
        updated = queue.update_progress(job.id, 1.5)
        assert updated.progress == 1.0


class TestJobQueueListing:
    """Tests for job listing operations."""
    
    def test_list_all(self, session: Session) -> None:
        """Test listing all jobs."""
        queue = JobQueue(session)
        
        for i in range(10):
            queue.enqueue(JobType.PROPOSE, {"order": i})
        
        jobs = queue.list()
        assert len(jobs) == 10
    
    def test_list_by_status(self, session: Session) -> None:
        """Test listing jobs by status."""
        queue = JobQueue(session)
        
        for i in range(5):
            queue.enqueue(JobType.PROPOSE, {})
        
        # Start 2 jobs
        queue.dequeue()
        queue.dequeue()
        
        pending = queue.list(status=JobStatus.PENDING)
        assert len(pending) == 3
        
        running = queue.list(status=JobStatus.RUNNING)
        assert len(running) == 2
    
    def test_list_by_campaign(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test listing jobs by campaign."""
        queue = JobQueue(session)
        
        # Jobs with campaign
        for i in range(3):
            queue.enqueue(JobType.PROPOSE, {}, sample_campaign.id)
        
        # Jobs without campaign
        for i in range(2):
            queue.enqueue(JobType.BENCHMARK, {})
        
        campaign_jobs = queue.list(campaign_id=sample_campaign.id)
        assert len(campaign_jobs) == 3
    
    def test_list_by_type(self, session: Session) -> None:
        """Test listing jobs by type."""
        queue = JobQueue(session)
        
        for i in range(3):
            queue.enqueue(JobType.PROPOSE, {})
        for i in range(2):
            queue.enqueue(JobType.BENCHMARK, {})
        
        propose_jobs = queue.list(job_type=JobType.PROPOSE)
        assert len(propose_jobs) == 3
        
        benchmark_jobs = queue.list(job_type=JobType.BENCHMARK)
        assert len(benchmark_jobs) == 2
    
    def test_list_pagination(self, session: Session) -> None:
        """Test job list pagination."""
        queue = JobQueue(session)
        
        for i in range(20):
            queue.enqueue(JobType.PROPOSE, {"order": i})
        
        page1 = queue.list(limit=5, offset=0)
        page2 = queue.list(limit=5, offset=5)
        
        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0].id != page2[0].id


class TestJobQueueCounts:
    """Tests for job counting operations."""
    
    def test_pending_count(self, session: Session) -> None:
        """Test counting pending jobs."""
        queue = JobQueue(session)
        
        for i in range(5):
            queue.enqueue(JobType.PROPOSE, {})
        
        queue.dequeue()  # Start one
        
        assert queue.pending_count() == 4
    
    def test_running_count(self, session: Session) -> None:
        """Test counting running jobs."""
        queue = JobQueue(session)
        
        for i in range(5):
            queue.enqueue(JobType.PROPOSE, {})
        
        queue.dequeue()
        queue.dequeue()
        
        assert queue.running_count() == 2
    
    def test_counts_by_campaign(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test counting jobs by campaign."""
        queue = JobQueue(session)
        
        # Jobs for campaign
        for i in range(3):
            queue.enqueue(JobType.PROPOSE, {}, sample_campaign.id)
        
        # Jobs without campaign
        for i in range(2):
            queue.enqueue(JobType.PROPOSE, {})
        
        assert queue.pending_count(sample_campaign.id) == 3
        assert queue.pending_count() == 5


class TestJobQueueCleanup:
    """Tests for job cleanup operations."""
    
    def test_cleanup_stale_jobs(self, session: Session) -> None:
        """Test cleaning up stale running jobs."""
        queue = JobQueue(session)
        
        job = queue.enqueue(JobType.PROPOSE, {})
        queue.dequeue()
        
        # Manually set started_at to old time
        job.started_at = datetime.utcnow() - timedelta(hours=48)
        session.add(job)
        session.commit()
        
        count = queue.cleanup_stale(max_age_hours=24)
        assert count == 1
        
        session.refresh(job)
        assert job.status == JobStatus.FAILED
        assert "timed out" in job.error.lower()
    
    def test_cleanup_completed_jobs(self, session: Session) -> None:
        """Test cleaning up old completed jobs."""
        queue = JobQueue(session)
        
        # Create and complete many jobs
        for i in range(20):
            job = queue.enqueue(JobType.PROPOSE, {})
            queue.dequeue()
            queue.complete(job.id, {})
        
        count = queue.cleanup_completed(keep_last=5)
        assert count == 15
        
        remaining = queue.list(status=JobStatus.COMPLETED)
        assert len(remaining) == 5

