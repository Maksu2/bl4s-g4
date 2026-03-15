"""
SQLAlchemy models for Geant4 Simulation Dashboard.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from datetime import datetime
import enum

from .database import Base


class JobStatus(str, enum.Enum):
    """Status of a simulation job."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base):
    """A single simulation job."""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    
    # Simulation parameters
    particles = Column(Integer, nullable=False)
    energy = Column(String(50), nullable=False)  # e.g., "1 GeV"
    thickness = Column(String(50), nullable=False)  # e.g., "1 cm"
    cycles = Column(Integer, default=1)
    generate_svg = Column(Boolean, default=True)
    
    # Status
    status = Column(String(20), default=JobStatus.PENDING.value)
    progress = Column(Integer, default=0)  # 0-100
    current_cycle = Column(Integer, default=0)
    
    # Results
    result_folder = Column(String(500), nullable=True)
    csv_files = Column(Text, nullable=True)  # JSON list of CSV file paths
    svg_files = Column(Text, nullable=True)  # JSON list of SVG file paths
    total_hits = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Metadata
    submitted_by = Column(String(100), nullable=True)  # Optional user identifier


class SystemState(Base):
    """Global system state singleton."""
    __tablename__ = "system_state"
    
    id = Column(Integer, primary_key=True, default=1)
    is_running = Column(Boolean, default=False)
    current_job_id = Column(Integer, nullable=True)
    last_activity = Column(DateTime, default=func.now())
