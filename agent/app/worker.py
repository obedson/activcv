"""
Background worker for processing jobs
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from app.core.database import get_db
from app.services.job_processor import JobProcessor
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JobWorker:
    """Background job worker"""
    
    def __init__(self):
        self.db = get_db()
        self.processor = JobProcessor(self.db)
        self.running = False
        self.current_job: Optional[str] = None
    
    async def start(self):
        """Start the worker"""
        logger.info("Starting job worker...")
        self.running = True
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            await self._worker_loop()
        except Exception as e:
            logger.error(f"Worker error: {e}")
        finally:
            logger.info("Job worker stopped")
    
    async def _worker_loop(self):
        """Main worker loop"""
        while self.running:
            try:
                # Get next job
                job = await self.processor.get_next_job()
                
                if job:
                    logger.info(f"Processing job {job.id} of type {job.job_type}")
                    self.current_job = job.id
                    
                    # Process job
                    success = await self.processor.process_job(job)
                    
                    if success:
                        logger.info(f"Job {job.id} completed successfully")
                    else:
                        logger.error(f"Job {job.id} failed")
                    
                    self.current_job = None
                else:
                    # No jobs available, wait before checking again
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        
        if self.current_job:
            logger.info(f"Waiting for current job {self.current_job} to complete...")
    
    async def stop(self):
        """Stop the worker"""
        self.running = False


async def main():
    """Main entry point"""
    worker = JobWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())