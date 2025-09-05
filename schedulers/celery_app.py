"""Celery application configuration for task scheduling."""
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta
import pytz

from config import settings

# Create Celery app
app = Celery('aicommissioner')

# Configure Celery
app.conf.update(
    broker_url=settings.redis_url,
    result_backend=settings.redis_url,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone=settings.default_timezone,
    enable_utc=True,
    
    # Task routes
    task_routes={
        'schedulers.tasks.run_weekly_power_rankings': {'queue': 'recaps'},
        'schedulers.tasks.run_weekly_waiver_recaps': {'queue': 'recaps'},
        'schedulers.tasks.sync_all_leagues': {'queue': 'sync'},
        'schedulers.tasks.cleanup_old_data': {'queue': 'maintenance'},
    },
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    
    # Task time limits
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    
    # Result settings
    result_expires=3600,  # 1 hour
    
    # Beat schedule for recurring tasks
    beat_schedule={
        # Power Rankings - Tuesday 9:00 AM Chicago time
        'weekly-power-rankings': {
            'task': 'schedulers.tasks.run_weekly_power_rankings',
            'schedule': crontab(
                hour=14,        # 14 UTC = 9 AM Central (accounting for CDT)
                minute=0,
                day_of_week=2   # Tuesday
            ),
        },
        
        # Waiver Recaps - Wednesday 9:00 AM Chicago time
        'weekly-waiver-recaps': {
            'task': 'schedulers.tasks.run_weekly_waiver_recaps',
            'schedule': crontab(
                hour=14,        # 14 UTC = 9 AM Central (accounting for CDT)
                minute=0,
                day_of_week=3   # Wednesday
            ),
        },
        
        # Sync all leagues - Daily at 6 AM Chicago time
        'daily-league-sync': {
            'task': 'schedulers.tasks.sync_all_leagues',
            'schedule': crontab(
                hour=11,        # 11 UTC = 6 AM Central
                minute=0
            ),
        },
        
        # Sync all leagues again - Daily at 6 PM Chicago time (during season)
        'evening-league-sync': {
            'task': 'schedulers.tasks.sync_all_leagues',
            'schedule': crontab(
                hour=23,        # 23 UTC = 6 PM Central
                minute=0
            ),
        },
        
        # Quick sync during game times - Sunday/Monday during football season
        'gameday-sync': {
            'task': 'schedulers.tasks.sync_all_leagues',
            'schedule': crontab(
                hour='*/2',     # Every 2 hours
                minute=0,
                day_of_week='0,1'  # Sunday and Monday
            ),
        },
        
        # Cleanup old data - Weekly on Sunday at 2 AM Chicago time
        'weekly-cleanup': {
            'task': 'schedulers.tasks.cleanup_old_data',
            'schedule': crontab(
                hour=7,         # 7 UTC = 2 AM Central
                minute=0,
                day_of_week=0   # Sunday
            ),
        },
        
        # Health check - Every 15 minutes
        'health-check': {
            'task': 'schedulers.tasks.health_check',
            'schedule': timedelta(minutes=15),
        },
    },
)

# Import tasks to register them
from schedulers import tasks

# Make the app discoverable
if __name__ == '__main__':
    app.start()
