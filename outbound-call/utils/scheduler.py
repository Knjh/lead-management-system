# utils/scheduler.py
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from services.lead_service import LeadService
from config.settings import settings

class CallScheduler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scheduler = AsyncIOScheduler()
        self.lead_service = LeadService()
    
    async def start_scheduler(self):
        """Start the scheduled calling jobs"""
        try:
            # Schedule calling job every 10 minutes during business hours
            self.scheduler.add_job(
                func=self._execute_calling_job,
                trigger=CronTrigger(
                    minute=f"*/{settings.cron_interval_minutes}",
                    hour=f"{settings.calling_start_hour}-{settings.calling_end_hour}",
                    day_of_week="mon-fri"
                ),
                id='calling_job',
                name='Execute Calling Batch',
                misfire_grace_time=60,
                coalesce=True,
                max_instances=1
            )
            
            # Schedule cleanup job daily at midnight
            self.scheduler.add_job(
                func=self._cleanup_old_records,
                trigger=CronTrigger(hour=0, minute=0),
                id='cleanup_job',
                name='Daily Cleanup',
                misfire_grace_time=300
            )
            
            self.scheduler.start()
            self.logger.info("Call scheduler started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting scheduler: {str(e)}")
            raise
    
    async def stop_scheduler(self):
        """Stop the scheduler"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                self.logger.info("Call scheduler stopped")
        except Exception as e:
            self.logger.error(f"Error stopping scheduler: {str(e)}")
    
    async def _execute_calling_job(self):
        """Execute the main calling job"""
        try:
            self.logger.info("Starting scheduled calling batch")
            result = await self.lead_service.execute_calling_batch()
            self.logger.info(f"Calling batch completed: {result}")
            
        except Exception as e:
            self.logger.error(f"Error in scheduled calling job: {str(e)}")
    
    async def _cleanup_old_records(self):
        """Clean up old records and logs"""
        try:
            self.logger.info("Starting daily cleanup job")
            # Add cleanup logic here if needed
            # e.g., remove old completed calls, archive old leads, etc.
            
        except Exception as e:
            self.logger.error(f"Error in cleanup job: {str(e)}")