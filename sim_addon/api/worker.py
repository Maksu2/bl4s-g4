"""
Background worker for executing Geant4 simulations.
Runs jobs sequentially from the queue.
"""

import asyncio
import subprocess
import os
import re
import shutil
import json
from datetime import datetime
from typing import Optional
import threading

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Job, SystemState, JobStatus
from .websocket import manager


class SimulationWorker:
    """Worker that processes simulation jobs sequentially."""
    
    def __init__(self):
        self.is_running = False
        self.should_stop = False
        self._task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Paths relative to project root (configurable via env for Docker)
        self.project_root = os.environ.get(
            "PROJECT_ROOT", 
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.geant_executable = os.environ.get(
            "GEANT_EXECUTABLE",
            os.path.join(self.project_root, "build", "GeantSim")
        )
        self.visualize_script = os.environ.get(
            "VISUALIZE_SCRIPT",
            os.path.join(self.project_root, "visualize_results.py")
        )
        self.results_dir = os.environ.get(
            "RESULTS_DIR",
            self.project_root
        )
    
    def start(self, loop: asyncio.AbstractEventLoop):
        """Start the worker in the background."""
        if self.is_running:
            return
        
        self._loop = loop
        self.should_stop = False
        self._task = loop.create_task(self._run_loop())
    
    def stop(self):
        """Signal the worker to stop."""
        self.should_stop = True
    
    async def _run_loop(self):
        """Main processing loop."""
        self.is_running = True
        
        try:
            await manager.send_system_status("running", True)
            await manager.send_log("🚀 Queue processing started", "info")
            
            while not self.should_stop:
                db = SessionLocal()
                try:
                    # Get next pending job
                    job = db.query(Job).filter(
                        Job.status.in_([JobStatus.PENDING.value, JobStatus.QUEUED.value])
                    ).order_by(Job.created_at).first()
                    
                    if not job:
                        # No more jobs, stop processing
                        break
                    
                    # Update system state
                    state = db.query(SystemState).first()
                    if not state:
                        state = SystemState(id=1, is_running=True)
                        db.add(state)
                    state.is_running = True
                    state.current_job_id = job.id
                    state.last_activity = datetime.now()
                    db.commit()
                    
                    # Process the job
                    await self._process_job(db, job)
                    
                finally:
                    db.close()
                
                # Small delay between jobs
                await asyncio.sleep(0.5)
            
        finally:
            self.is_running = False
            
            # Update system state
            db = SessionLocal()
            try:
                state = db.query(SystemState).first()
                if state:
                    state.is_running = False
                    state.current_job_id = None
                    db.commit()
            finally:
                db.close()
            
            await manager.send_system_status("ready", False)
            await manager.send_log("🏁 Queue processing completed", "info")
    
    async def _process_job(self, db: Session, job: Job):
        """Process a single simulation job."""
        try:
            # Update job status
            job.status = JobStatus.RUNNING.value
            job.started_at = datetime.now()
            db.commit()
            
            await manager.send_job_update(job.id, "running", 0, 0, 
                                          f"Starting simulation: {job.energy}, {job.particles} particles")
            await manager.send_log(f"▶ Starting Job #{job.id}: {job.energy}, {job.particles} particles, {job.thickness}", 
                                   "info", job.id)
            
            # Create result folder
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            result_folder = os.path.join(self.results_dir, f"Results_Web_{timestamp}_job{job.id}")
            os.makedirs(result_folder, exist_ok=True)
            job.result_folder = result_folder
            
            csv_files = []
            svg_files = []
            total_hits = 0
            
            # Run cycles
            for cycle in range(1, job.cycles + 1):
                if self.should_stop:
                    job.status = JobStatus.CANCELLED.value
                    db.commit()
                    await manager.send_job_update(job.id, "cancelled", 0, cycle, "Cancelled by user")
                    return
                
                # Update progress
                progress = int((cycle - 1) / job.cycles * 100)
                job.current_cycle = cycle
                job.progress = progress
                db.commit()
                
                await manager.send_job_update(job.id, "running", progress, cycle,
                                              f"Cycle {cycle}/{job.cycles}")
                
                # Create macro file
                mac_content = f"""
/det/setLeadThickness {job.thickness}
/run/initialize
/gun/particle e-
/gun/energy {job.energy}
/run/beamOn {job.particles}
"""
                mac_file = os.path.join(self.project_root, f"temp_web_job_{job.id}_cycle{cycle}.mac")
                
                try:
                    with open(mac_file, "w") as f:
                        f.write(mac_content)
                    
                    # Run Geant4 simulation
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: subprocess.run(
                            [self.geant_executable, mac_file],
                            capture_output=True,
                            text=True,
                            cwd=self.project_root
                        )
                    )
                    
                    if result.returncode != 0:
                        await manager.send_log(f"❌ Cycle {cycle} error: {result.stderr[:200]}", 
                                              "error", job.id)
                        continue
                    
                    # Parse output for CSV filename
                    match = re.search(r"Results written to\s+['\"]?(.*?\.csv)['\"]?", result.stdout)
                    
                    if match:
                        csv_filename = match.group(1)
                        csv_path = os.path.join(self.project_root, csv_filename)
                        
                        # Check total hits
                        cycle_hits = 0
                        try:
                            with open(csv_path, 'r') as cf:
                                next(cf, None)  # Skip header
                                for line in cf:
                                    parts = line.strip().split(',')
                                    if len(parts) >= 3:
                                        cycle_hits += int(parts[2])
                        except Exception:
                            pass
                        
                        if cycle_hits == 0:
                            await manager.send_log(f"   🚫 Cycle {cycle}: 0 hits - discarded", "warning", job.id)
                            if os.path.exists(csv_path):
                                os.remove(csv_path)
                        else:
                            total_hits += cycle_hits
                            await manager.send_log(f"   ✔ Cycle {cycle}: {csv_filename} ({cycle_hits} hits)", 
                                                  "info", job.id)
                            
                            # Generate SVG if requested
                            if job.generate_svg:
                                import sys
                                vis_result = await asyncio.get_event_loop().run_in_executor(
                                    None,
                                    lambda: subprocess.run(
                                        [
                                            sys.executable, self.visualize_script,
                                            csv_path,
                                            "--energy", job.energy,
                                            "--electrons", str(job.particles),
                                            "--thickness", job.thickness
                                        ],
                                        capture_output=True,
                                        text=True,
                                        cwd=self.project_root
                                    )
                                )
                            
                            # Move files to result folder
                            dest_csv = os.path.join(result_folder, os.path.basename(csv_filename))
                            if os.path.exists(csv_path):
                                shutil.move(csv_path, dest_csv)
                                csv_files.append(os.path.basename(csv_filename))
                            
                            svg_filename = csv_filename.replace(".csv", ".svg")
                            svg_path = os.path.join(self.project_root, svg_filename)
                            if os.path.exists(svg_path):
                                dest_svg = os.path.join(result_folder, os.path.basename(svg_filename))
                                shutil.move(svg_path, dest_svg)
                                svg_files.append(os.path.basename(svg_filename))
                    
                finally:
                    # Cleanup temp macro file
                    if os.path.exists(mac_file):
                        os.remove(mac_file)
            
            # Mark job as completed
            job.status = JobStatus.COMPLETED.value
            job.progress = 100
            job.completed_at = datetime.now()
            job.csv_files = json.dumps(csv_files)
            job.svg_files = json.dumps(svg_files)
            job.total_hits = total_hits
            db.commit()
            
            await manager.send_job_update(job.id, "completed", 100, job.cycles,
                                          f"Completed: {total_hits} total hits")
            await manager.send_log(f"✅ Job #{job.id} completed: {total_hits} total hits", "success", job.id)
            
            # Check storage and cleanup if needed
            await self._cleanup_if_needed(db)
            
        except Exception as e:
            job.status = JobStatus.FAILED.value
            job.error_message = str(e)
            job.completed_at = datetime.now()
            db.commit()
            
            await manager.send_job_update(job.id, "failed", job.progress, job.current_cycle, str(e))
            await manager.send_log(f"💥 Job #{job.id} failed: {str(e)}", "error", job.id)
    
    async def _cleanup_if_needed(self, db: Session):
        """Remove old results if storage exceeds 2GB."""
        storage_limit = 2 * 1024 * 1024 * 1024  # 2GB
        
        # Calculate current storage
        total_size = 0
        jobs_with_folders = db.query(Job).filter(Job.result_folder.isnot(None)).order_by(Job.created_at).all()
        
        for job in jobs_with_folders:
            if job.result_folder and os.path.exists(job.result_folder):
                for root, dirs, files in os.walk(job.result_folder):
                    for f in files:
                        total_size += os.path.getsize(os.path.join(root, f))
        
        # Delete oldest jobs until under limit
        while total_size > storage_limit and jobs_with_folders:
            oldest = jobs_with_folders.pop(0)
            if oldest.result_folder and os.path.exists(oldest.result_folder):
                folder_size = 0
                for root, dirs, files in os.walk(oldest.result_folder):
                    for f in files:
                        folder_size += os.path.getsize(os.path.join(root, f))
                
                shutil.rmtree(oldest.result_folder)
                oldest.result_folder = None
                oldest.csv_files = None
                oldest.svg_files = None
                db.commit()
                
                total_size -= folder_size
                await manager.send_log(f"🗑️ Cleaned up Job #{oldest.id} to free space", "warning")


# Global worker instance
worker = SimulationWorker()
