
import os
from app import app, bot_thread, scheduler_thread

if __name__ == "__main__":
    # Start bot and scheduler threads
    if bot_thread:
        bot_thread.start()
    if scheduler_thread:
        scheduler_thread.start()
        
    # Run Flask app
    port = os.getenv('PORT', 5000)
    app.run(host="0.0.0.0", port=port)
