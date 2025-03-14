import os
import logging
from flask import Flask, render_template, flash, redirect, url_for, request
from bot.telegram_bot import start_bot
from services.scheduler import start_scheduler
from models import db, User, Game, Subscription, PriceRecord, Store
import threading

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Create database tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

# Home route
@app.route('/')
def home():
    telegram_token = os.environ.get("TELEGRAM_TOKEN")
    bot_status = "active" if telegram_token else "inactive"
    return render_template('index.html', bot_status=bot_status)

# Settings route
@app.route('/settings')
def settings():
    telegram_token = os.environ.get("TELEGRAM_TOKEN", "")
    # Mask the token for security if it exists
    masked_token = "•" * len(telegram_token) if telegram_token else ""
    return render_template('settings.html', 
                          telegram_token=masked_token,
                          bot_status="active" if telegram_token else "inactive")

# Start the bot in a separate thread
def run_bot():
    try:
        logger.info("Starting Telegram bot...")
        bot = start_bot()
        if bot is None:
            logger.warning("Telegram bot not started. Use the web interface to set up the bot.")
    except Exception as e:
        logger.error(f"Error starting Telegram bot: {e}")

# Start the price tracker scheduler in a separate thread
def run_scheduler():
    try:
        logger.info("Starting price tracker scheduler...")
        # Pass app instance to scheduler
        start_scheduler(app)
    except Exception as e:
        logger.error(f"Error starting price tracker scheduler: {e}")

# Start the bot and scheduler when the app starts
bot_thread = threading.Thread(target=run_bot)
bot_thread.daemon = True
bot_thread.start()

scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True
scheduler_thread.start()

logger.info("App initialized successfully")
