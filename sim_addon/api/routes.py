"""
API routes for Geant4 Simulation Dashboard.
"""

import os
import json
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .database import get_db
from .models import Job, SystemState, JobStatus
from .schemas import (
    JobCreate, JobResponse, JobListItem, SystemStatus, 
    QueueStartRequest, AuthRequest
)
from .worker import worker
from .websocket import manager

router = APIRouter(prefix="/api", tags=["api"])

# Simple PIN authentication
VALID_PIN = "Ge@nt"


def verify_pin(pin: str) -> bool:
    """Verify the team PIN."""
    return pin == VALID_PIN


@router.post("/auth")
async def authenticate(request: AuthRequest):
    """Authenticate with team PIN."""
    if verify_pin(request.pin):
        return {"success": True, "message": "Authenticated"}
    raise HTTPException(status_code=401, detail="Invalid PIN")


@router.post("/jobs", response_model=JobResponse)
async def create_job(job: JobCreate, db: Session = Depends(get_db)):
    """Add a new job to the queue."""
    db_job = Job(
        name=job.name or f"Sim_{datetime.now().strftime('%H%M%S')}",
        particles=job.particles,
        energy=job.energy,
        thickness=job.thickness,
        cycles=job.cycles,
        generate_svg=job.generate_svg,
        status=JobStatus.PENDING.value
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    # Broadcast update
    await manager.send_log(f"➕ Job #{db_job.id} added to queue", "info", db_job.id)
    
    return _job_to_response(db_job)


@router.get("/jobs", response_model=List[JobListItem])
async def list_jobs(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List all jobs, optionally filtered by status."""
    query = db.query(Job)
    
    if status:
        query = query.filter(Job.status == status)
    
    jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()
    return [_job_to_list_item(j) for j in jobs]


@router.get("/jobs/queue", response_model=List[JobListItem])
async def get_queue(db: Session = Depends(get_db)):
    """Get current queue (pending and running jobs)."""
    jobs = db.query(Job).filter(
        Job.status.in_([JobStatus.PENDING.value, JobStatus.QUEUED.value, JobStatus.RUNNING.value])
    ).order_by(Job.created_at).all()
    return [_job_to_list_item(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: int, db: Session = Depends(get_db)):
    """Delete a job from the queue (only if pending)."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in [JobStatus.PENDING.value, JobStatus.COMPLETED.value, JobStatus.FAILED.value]:
        raise HTTPException(status_code=400, detail="Cannot delete running job")
    
    # Delete result folder if exists
    if job.result_folder and os.path.exists(job.result_folder):
        import shutil
        shutil.rmtree(job.result_folder)
    
    db.delete(job)
    db.commit()
    
    await manager.send_log(f"🗑️ Job #{job_id} deleted", "info")
    return {"success": True}


@router.get("/jobs/{job_id}/results/csv/{filename}")
async def download_csv(job_id: int, filename: str, db: Session = Depends(get_db)):
    """Download a CSV result file."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job or not job.result_folder:
        raise HTTPException(status_code=404, detail="Job or results not found")
    
    file_path = os.path.join(job.result_folder, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path, media_type="text/csv", filename=filename)


@router.get("/jobs/{job_id}/results/svg/{filename}")
async def download_svg(job_id: int, filename: str, db: Session = Depends(get_db)):
    """Download an SVG visualization file."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job or not job.result_folder:
        raise HTTPException(status_code=404, detail="Job or results not found")
    
    file_path = os.path.join(job.result_folder, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path, media_type="image/svg+xml", filename=filename)


@router.get("/jobs/{job_id}/results/svg/{filename}/view")
async def view_svg(job_id: int, filename: str, db: Session = Depends(get_db)):
    """Get SVG content for inline viewing."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job or not job.result_folder:
        raise HTTPException(status_code=404, detail="Job or results not found")
    
    file_path = os.path.join(job.result_folder, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    with open(file_path, "r") as f:
        return {"svg": f.read()}


@router.get("/jobs/{job_id}/results/csv/{filename}/preview")
async def preview_csv(job_id: int, filename: str, limit: int = 50, db: Session = Depends(get_db)):
    """Get CSV data preview for table display."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job or not job.result_folder:
        raise HTTPException(status_code=404, detail="Job or results not found")
    
    file_path = os.path.join(job.result_folder, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    rows = []
    with open(file_path, "r") as f:
        header = f.readline().strip().split(",")
        for i, line in enumerate(f):
            if i >= limit:
                break
            rows.append(line.strip().split(","))
    
    return {"header": header, "rows": rows}


@router.post("/queue/start")
async def start_queue(db: Session = Depends(get_db)):
    """Start processing the queue."""
    if worker.is_running:
        raise HTTPException(status_code=400, detail="Queue is already running")
    
    # Check if there are pending jobs
    pending_count = db.query(Job).filter(
        Job.status.in_([JobStatus.PENDING.value, JobStatus.QUEUED.value])
    ).count()
    
    if pending_count == 0:
        raise HTTPException(status_code=400, detail="No jobs in queue")
    
    import asyncio
    loop = asyncio.get_event_loop()
    worker.start(loop)
    
    return {"success": True, "message": f"Started processing {pending_count} jobs"}


@router.post("/queue/stop")
async def stop_queue():
    """Stop processing the queue."""
    if not worker.is_running:
        raise HTTPException(status_code=400, detail="Queue is not running")
    
    worker.stop()
    return {"success": True, "message": "Queue stopping..."}


@router.get("/status", response_model=SystemStatus)
async def get_status(db: Session = Depends(get_db)):
    """Get current system status."""
    state = db.query(SystemState).first()
    
    queue_length = db.query(Job).filter(
        Job.status.in_([JobStatus.PENDING.value, JobStatus.QUEUED.value])
    ).count()
    
    total_jobs = db.query(Job).count()
    
    # Calculate storage
    storage_used = 0
    jobs_with_folders = db.query(Job).filter(Job.result_folder.isnot(None)).all()
    for job in jobs_with_folders:
        if job.result_folder and os.path.exists(job.result_folder):
            for root, dirs, files in os.walk(job.result_folder):
                for f in files:
                    try:
                        storage_used += os.path.getsize(os.path.join(root, f))
                    except:
                        pass
    
    # Determine status
    if worker.is_running:
        status = "running"
    elif queue_length > 0:
        status = "ready"
    else:
        status = "idle"
    
    return SystemStatus(
        status=status,
        is_running=worker.is_running,
        current_job_id=state.current_job_id if state else None,
        queue_length=queue_length,
        total_jobs=total_jobs,
        storage_used_bytes=storage_used,
        storage_limit_bytes=2 * 1024 * 1024 * 1024  # 2GB
    )


@router.get("/history", response_model=List[JobListItem])
async def get_history(
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get job history (completed and failed jobs)."""
    jobs = db.query(Job).filter(
        Job.status.in_([JobStatus.COMPLETED.value, JobStatus.FAILED.value])
    ).order_by(Job.completed_at.desc()).offset(offset).limit(limit).all()
    return [_job_to_list_item(j) for j in jobs]


def _job_to_response(job: Job) -> JobResponse:
    """Convert Job model to JobResponse schema."""
    csv_files = json.loads(job.csv_files) if job.csv_files else []
    svg_files = json.loads(job.svg_files) if job.svg_files else []
    
    return JobResponse(
        id=job.id,
        name=job.name,
        particles=job.particles,
        energy=job.energy,
        thickness=job.thickness,
        cycles=job.cycles,
        generate_svg=job.generate_svg,
        status=job.status,
        progress=job.progress,
        current_cycle=job.current_cycle,
        result_folder=job.result_folder,
        csv_files=csv_files,
        svg_files=svg_files,
        total_hits=job.total_hits,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        submitted_by=job.submitted_by
    )


def _job_to_list_item(job: Job) -> JobListItem:
    """Convert Job model to JobListItem schema."""
    return JobListItem(
        id=job.id,
        name=job.name,
        particles=job.particles,
        energy=job.energy,
        thickness=job.thickness,
        cycles=job.cycles,
        status=job.status,
        progress=job.progress,
        current_cycle=job.current_cycle,
        created_at=job.created_at
    )
