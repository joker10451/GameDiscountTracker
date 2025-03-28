import os
import logging
from flask import Flask, render_template, flash, redirect, url_for, request
from bot.telegram_bot import start_bot, run_bot as run_telegram_bot
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
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///gamebot.db"
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
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        # Handle token update
        new_token = request.form.get('telegram_token')
        if new_token:
            # TODO: In a production environment, we would store this in a more secure way
            # For this demo, we're using environment variables
            os.environ['TELEGRAM_TOKEN'] = new_token
            flash('Telegram token updated successfully. Restart the bot to apply changes.', 'success')
            return redirect(url_for('restart_bot'))
        else:
            flash('Please provide a valid Telegram token.', 'error')

    telegram_token = os.environ.get("TELEGRAM_TOKEN", "")
    # Mask the token for security if it exists
    masked_token = "•" * len(telegram_token) if telegram_token else ""
    return render_template('settings.html', 
                          telegram_token=masked_token,
                          bot_status="active" if telegram_token else "inactive")

# Restart bot route
@app.route('/restart_bot')
def restart_bot():
    global bot_thread

    # Check if thread is alive and terminate it if it is
    if bot_thread and bot_thread.is_alive():
        # We can't actually stop a running thread directly in Python
        # This is just a placeholder - in a real application we would 
        # implement a proper termination mechanism
        logger.info("Terminating existing bot thread...")
        # In a real application, we'd implement some signaling to the thread

    # Start a new bot thread
    logger.info("Starting new bot thread...")
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    flash('Bot restarted with new settings.', 'success')
    return redirect(url_for('settings'))

# Start the bot in a separate thread
def run_bot():
    try:
        logger.info("Starting Telegram bot...")
        # Initialize the bot with app context
        bot_app = start_bot(app)
        if bot_app is None:
            logger.warning("Telegram bot not started. Use the web interface to set up the bot.")
        else:
            # Run the bot with the initialized application and pass Flask app for context
            run_telegram_bot(bot_app, app)
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