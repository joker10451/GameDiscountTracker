import os
import logging
import asyncio
import threading
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from bot.handlers import start, help_command, search_games, subscribe_game, unsubscribe_game, list_subscriptions, check_discounts, button_handler, error_handler

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def start_bot(app=None):
    """Initialize and start the Telegram bot
    
    Args:
        app: Flask application instance for context (optional)
    
    Returns:
        The initialized application instance or None if failed
    """
    # Get token from environment variable
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    
    if not telegram_token:
        logger.warning("No Telegram token found in environment variables! Bot will not be started.")
        logger.info("Set the TELEGRAM_TOKEN environment variable to enable the bot.")
        return None
    
    try:
        # Create the Application instance
        application = ApplicationBuilder().token(telegram_token).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("search", search_games))
        application.add_handler(CommandHandler("subscribe", subscribe_game))
        application.add_handler(CommandHandler("unsubscribe", unsubscribe_game))
        application.add_handler(CommandHandler("mysubs", list_subscriptions))
        application.add_handler(CommandHandler("discounts", check_discounts))
        
        # Add callback query handler for inline buttons
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        return application
    except Exception as e:
        logger.error(f"Error initializing Telegram bot: {e}")
        return None

class BotThread(threading.Thread):
    """Thread class for running the Telegram bot with its own event loop"""
    
    def __init__(self, application):
        super().__init__()
        self.application = application
        self.daemon = True
        
    def run(self):
        """Run the bot in a new event loop"""
        if not self.application:
            logger.error("Cannot run bot: application not initialized.")
            return
        
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Define an async function to run the bot
            async def start_bot_async():
                await self.application.initialize()
                await self.application.start()
                await self.application.updater.start_polling()
                logger.info("Telegram bot polling started successfully")
            
            # Run the async function in the loop
            loop.run_until_complete(start_bot_async())
            loop.run_forever()
        except Exception as e:
            logger.error(f"Error running Telegram bot: {e}")
            
def run_bot(application):
    """Start the bot in a separate thread with its own event loop
    
    Args:
        application: The initialized Telegram application
    """
    if not application:
        logger.error("Cannot run bot: application not initialized.")
        return
    
    try:
        # Start the Bot in a dedicated thread
        logger.info("Starting Telegram bot in a separate thread...")
        bot_thread = BotThread(application)
        bot_thread.start()
        return bot_thread
    except Exception as e:
        logger.error(f"Error starting Telegram bot thread: {e}")
        return None
