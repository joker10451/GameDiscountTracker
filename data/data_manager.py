import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Data storage file paths
DATA_DIR = Path("data/storage")
SUBSCRIPTIONS_FILE = DATA_DIR / "subscriptions.json"
PRICES_FILE = DATA_DIR / "prices.json"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_json_data(file_path: Path) -> Dict:
    """
    Load JSON data from a file
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary with loaded data or empty dict if file doesn't exist
    """
    try:
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading data from {file_path}: {e}")
        return {}

def save_json_data(data: Dict, file_path: Path) -> bool:
    """
    Save data to a JSON file
    
    Args:
        data: Dictionary with data to save
        file_path: Path to the JSON file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving data to {file_path}: {e}")
        return False

def add_subscription(user_id: int, game_id: str, game_name: str) -> bool:
    """
    Add a game subscription for a user
    
    Args:
        user_id: Telegram user ID
        game_id: Game ID to subscribe to
        game_name: Name of the game
        
    Returns:
        True if subscription was added, False if already exists
    """
    # Load current subscriptions
    subscriptions = load_json_data(SUBSCRIPTIONS_FILE)
    
    # Convert user_id to string for JSON compatibility
    user_id_str = str(user_id)
    
    # Initialize user entry if not exists
    if user_id_str not in subscriptions:
        subscriptions[user_id_str] = {}
    
    # Check if already subscribed
    if game_id in subscriptions[user_id_str]:
        return False
    
    # Add subscription
    subscriptions[user_id_str][game_id] = {
        'name': game_name,
        'subscribed_at': str(Path().absolute())  # Using timestamp as string
    }
    
    # Save updated subscriptions
    return save_json_data(subscriptions, SUBSCRIPTIONS_FILE)

def remove_subscription(user_id: int, game_id: str) -> Tuple[bool, str]:
    """
    Remove a game subscription for a user
    
    Args:
        user_id: Telegram user ID
        game_id: Game ID to unsubscribe from
        
    Returns:
        Tuple of (success, game_name)
    """
    # Load current subscriptions
    subscriptions = load_json_data(SUBSCRIPTIONS_FILE)
    
    # Convert user_id to string for JSON compatibility
    user_id_str = str(user_id)
    
    # Check if user and game subscription exists
    if user_id_str not in subscriptions or game_id not in subscriptions[user_id_str]:
        return (False, "Unknown Game")
    
    # Get game name before removing
    game_name = subscriptions[user_id_str][game_id].get('name', 'Unknown Game')
    
    # Remove subscription
    del subscriptions[user_id_str][game_id]
    
    # Remove user entry if no more subscriptions
    if not subscriptions[user_id_str]:
        del subscriptions[user_id_str]
    
    # Save updated subscriptions
    success = save_json_data(subscriptions, SUBSCRIPTIONS_FILE)
    
    return (success, game_name)

def get_user_subscriptions(user_id: int) -> Dict[str, Dict[str, Any]]:
    """
    Get all game subscriptions for a user
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        Dictionary with game_id as keys and game info as values
    """
    # Load current subscriptions
    subscriptions = load_json_data(SUBSCRIPTIONS_FILE)
    
    # Convert user_id to string for JSON compatibility
    user_id_str = str(user_id)
    
    # Return user subscriptions or empty dict if none
    return subscriptions.get(user_id_str, {})

def get_all_subscriptions() -> Dict[str, List[str]]:
    """
    Get all game subscriptions grouped by game_id
    
    Returns:
        Dictionary with game_id as keys and list of user_ids as values
    """
    # Load current subscriptions
    subscriptions = load_json_data(SUBSCRIPTIONS_FILE)
    
    # Group by game_id
    game_subscriptions = {}
    
    for user_id, user_subs in subscriptions.items():
        for game_id in user_subs:
            if game_id not in game_subscriptions:
                game_subscriptions[game_id] = []
            game_subscriptions[game_id].append(user_id)
    
    return game_subscriptions

def get_subscribed_users_for_game(game_id: str) -> List[int]:
    """
    Get all users subscribed to a specific game
    
    Args:
        game_id: Game ID to check
        
    Returns:
        List of user IDs subscribed to the game
    """
    # Load current subscriptions
    subscriptions = load_json_data(SUBSCRIPTIONS_FILE)
    
    # Find all users subscribed to this game
    users = []
    
    for user_id, user_subs in subscriptions.items():
        if game_id in user_subs:
            # Convert back to integer
            users.append(int(user_id))
    
    return users

def update_game_price(game_id: str, store: str, price: float, discount_percent: int) -> Optional[Dict[str, Any]]:
    """
    Update or add price information for a game
    
    Args:
        game_id: Game ID
        store: Store name
        price: Current price
        discount_percent: Discount percentage
        
    Returns:
        Previous price information or None if no previous info
    """
    # Load current prices
    prices = load_json_data(PRICES_FILE)
    
    # Initialize game entry if not exists
    if game_id not in prices:
        prices[game_id] = {}
    
    # Get previous price data if exists
    previous_data = prices[game_id].get(store)
    
    # Update with new price
    prices[game_id][store] = {
        'price': price,
        'discount_percent': discount_percent,
        'updated_at': str(Path().absolute())  # Using timestamp as string
    }
    
    # Save updated prices
    save_json_data(prices, PRICES_FILE)
    
    return previous_data
