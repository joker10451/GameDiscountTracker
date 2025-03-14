import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from bot.handlers import start, help_command, search_games, subscribe_game, unsubscribe_game, list_subscriptions, check_discounts, button_handler, error_handler

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def start_bot():
    """Initialize and start the Telegram bot"""
    # Get token from environment variable
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    
    if not telegram_token:
        logger.error("No Telegram token found in environment variables!")
        raise ValueError("TELEGRAM_TOKEN environment variable is required")
    
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
    
    # Start the Bot
    logger.info("Starting Telegram bot polling...")
    application.run_polling()
    
    return application
