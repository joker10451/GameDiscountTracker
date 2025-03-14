import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.game_service import search_game, get_game_details
from services.price_tracker import get_current_discounts
from data.data_manager import add_subscription, remove_subscription, get_user_subscriptions, update_user_info
from flask import current_app

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    
    # Save user info to database
    with current_app.app_context():
        try:
            update_user_info(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            logger.info(f"User data saved to database: {user.id}")
        except Exception as e:
            logger.error(f"Error saving user data: {e}")
    
    await update.message.reply_html(
        f"Hi {user.mention_html()}! 👋\n\n"
        "I'm a Game Discount Tracker Bot. I can help you track price drops for your favorite games "
        "across various digital stores.\n\n"
        "Use /help to see the list of available commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "Here are the commands you can use:\n\n"
        "/search <game_name> - Search for a game\n"
        "/subscribe <game_id> - Subscribe to price alerts for a game\n"
        "/unsubscribe <game_id> - Unsubscribe from price alerts\n"
        "/mysubs - List your subscribed games\n"
        "/discounts - Show current discounts\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(help_text)

async def search_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for games when the command /search is issued."""
    if not context.args:
        await update.message.reply_text("Please provide a game name to search for. Example: /search Witcher 3")
        return
    
    query = ' '.join(context.args)
    await update.message.reply_text(f"Searching for: {query}...")
    
    try:
        results = await search_game(query)
        
        if not results:
            await update.message.reply_text(f"No games found for '{query}'. Please try a different search term.")
            return
        
        # Create reply with inline buttons for each result
        reply_text = "🎮 Search Results:\n\n"
        keyboard = []
        
        for idx, game in enumerate(results[:5]):  # Limit to 5 results to avoid message size limits
            game_id = game.get('id')
            game_name = game.get('name')
            
            reply_text += f"{idx+1}. {game_name} (ID: {game_id})\n"
            
            # Add button to subscribe and view details
            keyboard.append([
                InlineKeyboardButton(f"Subscribe to {game_name}", callback_data=f"sub_{game_id}"),
                InlineKeyboardButton(f"Details", callback_data=f"details_{game_id}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(reply_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in search_games: {e}")
        await update.message.reply_text(f"Sorry, there was an error while searching. Please try again later.")

async def subscribe_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Subscribe to price alerts for a game."""
    if not context.args:
        await update.message.reply_text("Please provide a game ID to subscribe to. Use /search to find game IDs.")
        return
    
    game_id = context.args[0]
    user_id = update.effective_user.id
    
    try:
        # Get game details first to verify it exists
        game_details = await get_game_details(game_id)
        
        if not game_details:
            await update.message.reply_text(f"Game with ID {game_id} not found. Please check the ID and try again.")
            return
        
        # Add subscription with app context
        with current_app.app_context():
            # Get thumbnail if available
            thumbnail = game_details.get('thumbnail', None)
            success = add_subscription(user_id, game_id, game_details.get('name', 'Unknown Game'), thumbnail)
        
            if success:
                await update.message.reply_text(
                    f"✅ You are now subscribed to price alerts for {game_details.get('name')}.\n"
                    f"I'll notify you when the price drops!"
                )
            else:
                await update.message.reply_text(f"You're already subscribed to this game.")
            
    except Exception as e:
        logger.error(f"Error in subscribe_game: {e}")
        await update.message.reply_text("Sorry, there was an error while subscribing. Please try again later.")

async def unsubscribe_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unsubscribe from price alerts for a game."""
    if not context.args:
        await update.message.reply_text("Please provide a game ID to unsubscribe from. Use /mysubs to see your subscriptions.")
        return
    
    game_id = context.args[0]
    user_id = update.effective_user.id
    
    try:
        # Remove subscription with app context
        with current_app.app_context():
            success, game_name = remove_subscription(user_id, game_id)
        
            if success:
                await update.message.reply_text(f"✅ You have unsubscribed from price alerts for {game_name}.")
            else:
                await update.message.reply_text("You're not subscribed to this game.")
            
    except Exception as e:
        logger.error(f"Error in unsubscribe_game: {e}")
        await update.message.reply_text("Sorry, there was an error while unsubscribing. Please try again later.")

async def list_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all subscribed games for the user."""
    user_id = update.effective_user.id
    
    try:
        subscriptions = get_user_subscriptions(user_id)
        
        if not subscriptions:
            await update.message.reply_text(
                "You don't have any game subscriptions yet.\n"
                "Use /search to find games and subscribe to them!"
            )
            return
        
        reply_text = "🎮 Your Game Subscriptions:\n\n"
        keyboard = []
        
        for game_id, game_info in subscriptions.items():
            game_name = game_info.get('name', 'Unknown Game')
            reply_text += f"• {game_name} (ID: {game_id})\n"
            
            # Add button to unsubscribe
            keyboard.append([
                InlineKeyboardButton(f"Unsubscribe from {game_name}", callback_data=f"unsub_{game_id}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(reply_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in list_subscriptions: {e}")
        await update.message.reply_text("Sorry, there was an error retrieving your subscriptions. Please try again later.")

async def check_discounts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current game discounts."""
    await update.message.reply_text("Checking current game discounts... This might take a moment.")
    
    try:
        discounts = await get_current_discounts()
        
        if not discounts:
            await update.message.reply_text("No notable discounts found at the moment. Check back later!")
            return
        
        reply_text = "🔥 Current Hot Deals:\n\n"
        keyboard = []
        
        for game in discounts[:10]:  # Limit to 10 games to avoid message size limits
            game_id = game.get('id')
            game_name = game.get('name')
            discount = game.get('discount_percent', 0)
            current_price = game.get('price_current', 'Unknown')
            original_price = game.get('price_original', 'Unknown')
            store = game.get('store', 'Unknown Store')
            
            reply_text += (f"🎮 {game_name}\n"
                         f"💰 {current_price} (was {original_price}, -{discount}%)\n"
                         f"🏪 {store}\n\n")
            
            # Add button to subscribe
            keyboard.append([
                InlineKeyboardButton(f"Subscribe to {game_name}", callback_data=f"sub_{game_id}"),
                InlineKeyboardButton(f"Details", callback_data=f"details_{game_id}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(reply_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in check_discounts: {e}")
        await update.message.reply_text("Sorry, there was an error retrieving current discounts. Please try again later.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    try:
        if data.startswith('sub_'):
            game_id = data[4:]
            user_id = update.effective_user.id
            
            # Get game details
            game_details = await get_game_details(game_id)
            
            if not game_details:
                await query.edit_message_text(text=f"Game with ID {game_id} not found. Please try another game.")
                return
            
            # Add subscription
            success = add_subscription(user_id, game_id, game_details.get('name', 'Unknown Game'))
            
            if success:
                await query.edit_message_text(
                    text=f"✅ You are now subscribed to price alerts for {game_details.get('name')}.\n"
                         f"I'll notify you when the price drops!"
                )
            else:
                await query.edit_message_text(text=f"You're already subscribed to this game.")
                
        elif data.startswith('unsub_'):
            game_id = data[6:]
            user_id = update.effective_user.id
            
            # Remove subscription
            success, game_name = remove_subscription(user_id, game_id)
            
            if success:
                await query.edit_message_text(text=f"✅ You have unsubscribed from price alerts for {game_name}.")
            else:
                await query.edit_message_text(text="You're not subscribed to this game.")
                
        elif data.startswith('details_'):
            game_id = data[8:]
            
            # Get game details
            game_details = await get_game_details(game_id)
            
            if not game_details:
                await query.edit_message_text(text=f"Game with ID {game_id} not found. Please try another game.")
                return
            
            # Format game details message
            game_name = game_details.get('name', 'Unknown Game')
            stores = game_details.get('stores', [])
            prices = game_details.get('prices', {})
            
            details_text = f"🎮 {game_name}\n\n"
            
            if 'description' in game_details:
                # Truncate description if it's too long
                description = game_details['description']
                if len(description) > 200:
                    description = description[:197] + "..."
                details_text += f"📝 {description}\n\n"
            
            details_text += "💰 Prices:\n"
            
            for store_name, price_info in prices.items():
                current_price = price_info.get('current', 'Unknown')
                original_price = price_info.get('original', 'Unknown')
                discount = price_info.get('discount_percent', 0)
                
                if discount > 0:
                    details_text += f"🏪 {store_name}: {current_price} (was {original_price}, -{discount}%)\n"
                else:
                    details_text += f"🏪 {store_name}: {current_price}\n"
            
            # Add button to subscribe
            keyboard = [[InlineKeyboardButton(f"Subscribe to {game_name}", callback_data=f"sub_{game_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text=details_text, reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Error in button_handler: {e}")
        await query.edit_message_text(text="Sorry, there was an error processing your request. Please try again later.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Notify user of error
    if update.effective_message:
        await update.effective_message.reply_text("Sorry, something went wrong. Please try again later.")
