import logging
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from services.price_tracker import check_price_updates, send_price_drop_notifications

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create a scheduler
scheduler = BackgroundScheduler()

async def scheduled_price_check():
    """Job to check prices and send notifications"""
    try:
        logger.info("Running scheduled price check...")
        price_drops = await check_price_updates()
        await send_price_drop_notifications(price_drops)
        logger.info("Scheduled price check completed.")
    except Exception as e:
        logger.error(f"Error in scheduled price check: {e}")

def run_async_job():
    """Run the async scheduled job in the current event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(scheduled_price_check())

def start_scheduler():
    """Start the APScheduler for price checking"""
    if scheduler.running:
        logger.info("Scheduler is already running.")
        return

    try:
        # Schedule price check job to run daily at midnight
        scheduler.add_job(
            run_async_job,
            trigger=CronTrigger(hour=0, minute=0),
            id='price_check_job',
            name='Daily price check',
            replace_existing=True
        )
        
        # Add another job to run every 4 hours for more frequent checks
        scheduler.add_job(
            run_async_job,
            trigger=CronTrigger(hour='*/4'),
            id='price_check_frequent_job',
            name='Frequent price check',
            replace_existing=True
        )
        
        # Start the scheduler
        scheduler.start()
        logger.info("Price check scheduler started.")
        
        # Run job immediately on startup
        run_async_job()
        
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")

def stop_scheduler():
    """Stop the APScheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Price check scheduler stopped.")
