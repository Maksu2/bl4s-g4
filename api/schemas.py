"""
Pydantic schemas for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobCreate(BaseModel):
    """Schema for creating a new job."""
    name: Optional[str] = None
    particles: int = Field(..., gt=0, description="Number of particles")
    energy: str = Field(..., description="Beam energy, e.g. '1 GeV'")
    thickness: str = Field(..., description="Target thickness, e.g. '1 cm'")
    cycles: int = Field(default=1, ge=1, description="Number of cycles")
    generate_svg: bool = Field(default=True, description="Generate SVG visualization")


class JobResponse(BaseModel):
    """Schema for job response."""
    id: int
    name: Optional[str]
    particles: int
    energy: str
    thickness: str
    cycles: int
    generate_svg: bool
    status: str
    progress: int
    current_cycle: int
    result_folder: Optional[str]
    csv_files: Optional[List[str]]
    svg_files: Optional[List[str]]
    total_hits: int
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    submitted_by: Optional[str]

    class Config:
        from_attributes = True


class JobListItem(BaseModel):
    """Abbreviated job info for lists."""
    id: int
    name: Optional[str]
    particles: int
    energy: str
    thickness: str
    cycles: int
    status: str
    progress: int
    current_cycle: int
    created_at: datetime

    class Config:
        from_attributes = True


class SystemStatus(BaseModel):
    """Current system status."""
    status: str  # "ready", "running", "error"
    is_running: bool
    current_job_id: Optional[int]
    queue_length: int
    total_jobs: int
    storage_used_bytes: int
    storage_limit_bytes: int


class QueueStartRequest(BaseModel):
    """Request to start the queue."""
    pass


class LogEntry(BaseModel):
    """A log entry."""
    timestamp: datetime
    level: str
    message: str
    job_id: Optional[int] = None


class AuthRequest(BaseModel):
    """PIN authentication request."""
    pin: str
