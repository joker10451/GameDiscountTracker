import os
import logging
import aiohttp
from typing import Dict, List, Any, Optional
from data.data_manager import get_all_subscriptions, update_game_price, get_subscribed_users_for_game
from services.game_service import get_game_details

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# CheapShark API URL
CHEAPSHARK_API_URL = "https://www.cheapshark.com/api/1.0"

async def check_price_updates() -> Dict[str, Dict[str, Any]]:
    """
    Check price updates for all subscribed games
    
    Returns:
        A dictionary with game_id as keys and game information (including users to notify) as values
    """
    logger.info("Checking price updates for subscribed games...")
    
    # Get all game subscriptions
    all_subscriptions = get_all_subscriptions()
    
    if not all_subscriptions:
        logger.info("No subscriptions found.")
        return {}
    
    # Track games with price drops
    price_drops = {}
    
    # Check each game
    for game_id in all_subscriptions:
        try:
            # Get current game details from API
            game_details = await get_game_details(game_id)
            
            if not game_details:
                logger.warning(f"Could not get details for game ID: {game_id}")
                continue
            
            # Check if there's a price drop in any store
            has_price_drop = False
            price_drop_info = {}
            
            for store_name, price_info in game_details.get('prices', {}).items():
                current_price = price_info.get('current', '0')
                discount_percent = price_info.get('discount_percent', 0)
                
                # Remove currency symbol for comparison
                try:
                    if current_price.startswith('$'):
                        current_price = current_price[1:]
                    current_price_float = float(current_price)
                except (ValueError, TypeError, AttributeError):
                    current_price_float = 0.0
                
                # Check if there's a significant discount (> 10%)
                if discount_percent > 10:
                    # Get previous price information
                    previous_info = update_game_price(game_id, store_name, current_price_float, discount_percent)
                    
                    if previous_info:
                        previous_price = previous_info.get('price', 0.0)
                        
                        # Check if price has dropped from previous record
                        if current_price_float < previous_price and previous_price > 0:
                            has_price_drop = True
                            price_drop_info[store_name] = {
                                'previous_price': f"${previous_price}",
                                'current_price': price_info.get('current'),
                                'discount_percent': discount_percent
                            }
                    else:
                        # First time tracking this price, consider it a drop if there's a discount
                        has_price_drop = True
                        price_drop_info[store_name] = {
                            'current_price': price_info.get('current'),
                            'original_price': price_info.get('original'),
                            'discount_percent': discount_percent
                        }
            
            # If price drop detected, add to notify list
            if has_price_drop:
                # Get users subscribed to this game
                users = get_subscribed_users_for_game(game_id)
                
                if users:
                    price_drops[game_id] = {
                        'name': game_details.get('name', 'Unknown Game'),
                        'users': users,
                        'price_info': price_drop_info
                    }
        
        except Exception as e:
            logger.error(f"Error checking price updates for game {game_id}: {e}")
    
    logger.info(f"Found {len(price_drops)} games with price drops.")
    return price_drops

async def send_price_drop_notifications(price_drops: Dict[str, Dict[str, Any]]) -> None:
    """
    Send notifications to users about price drops
    
    Args:
        price_drops: Dictionary with game information and users to notify
    """
    if not price_drops:
        logger.info("No price drops to notify users about.")
        return
    
    # Get the bot application instance
    try:
        from telegram.ext import ApplicationBuilder
        
        telegram_token = os.getenv("TELEGRAM_TOKEN")
        
        if not telegram_token:
            logger.error("No Telegram token found in environment variables!")
            return
        
        application = ApplicationBuilder().token(telegram_token).build()
        
        # Send notifications to each user
        for game_id, game_info in price_drops.items():
            game_name = game_info.get('name', 'Unknown Game')
            users = game_info.get('users', [])
            price_info = game_info.get('price_info', {})
            
            # Create notification message
            message = f"🔥 Price Drop Alert! 🔥\n\n"
            message += f"Game: {game_name}\n\n"
            
            for store_name, store_price_info in price_info.items():
                current_price = store_price_info.get('current_price', 'Unknown')
                
                if 'previous_price' in store_price_info:
                    previous_price = store_price_info.get('previous_price', 'Unknown')
                    discount = store_price_info.get('discount_percent', 0)
                    message += f"🏪 {store_name}: {current_price} (was {previous_price}, -{discount}%)\n"
                else:
                    original_price = store_price_info.get('original_price', 'Unknown')
                    discount = store_price_info.get('discount_percent', 0)
                    message += f"🏪 {store_name}: {current_price} (was {original_price}, -{discount}%)\n"
            
            # Add a call to action
            message += f"\nUse /search {game_name} to get more details!"
            
            # Send to each subscribed user
            for user_id in users:
                try:
                    await application.bot.send_message(chat_id=user_id, text=message)
                    logger.info(f"Sent price drop notification for {game_name} to user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to send notification to user {user_id}: {e}")
        
    except Exception as e:
        logger.error(f"Error sending price drop notifications: {e}")

async def get_current_discounts(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get current discounted games from CheapShark API
    
    Args:
        limit: Maximum number of deals to return
        
    Returns:
        A list of discounted games
    """
    try:
        async with aiohttp.ClientSession() as session:
            # Get deals sorted by savings
            deals_url = f"{CHEAPSHARK_API_URL}/deals?pageSize={limit}&sortBy=savings"
            
            async with session.get(deals_url) as response:
                if response.status != 200:
                    logger.error(f"API request failed with status {response.status}")
                    return []
                
                data = await response.json()
                
                # Format the response to our standard format
                results = []
                for deal in data:
                    # Get store name
                    store_id = deal.get('storeID')
                    store_url = f"{CHEAPSHARK_API_URL}/stores"
                    
                    store_name = "Unknown Store"
                    async with session.get(store_url) as store_response:
                        if store_response.status == 200:
                            stores = await store_response.json()
                            for store in stores:
                                if store.get('storeID') == store_id:
                                    store_name = store.get('storeName')
                                    break
                    
                    # Format the deal
                    results.append({
                        'id': deal.get('gameID'),
                        'name': deal.get('title'),
                        'store': store_name,
                        'price_current': f"${deal.get('salePrice')}",
                        'price_original': f"${deal.get('normalPrice')}",
                        'discount_percent': int(float(deal.get('savings', '0'))),
                        'deal_rating': deal.get('dealRating')
                    })
                
                return results
    except Exception as e:
        logger.error(f"Error getting current discounts: {e}")
        return []
