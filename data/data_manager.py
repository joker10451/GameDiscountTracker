import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from models import db, User, Game, Subscription, PriceRecord, Store

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_subscription(user_id: int, game_id: str, game_name: str, thumbnail: str = None) -> bool:
    """
    Add a game subscription for a user
    
    Args:
        user_id: Telegram user ID
        game_id: Game ID to subscribe to
        game_name: Name of the game
        thumbnail: Optional URL to game thumbnail
        
    Returns:
        True if subscription was added, False if already exists
    """
    try:
        # Check if user exists, create if not
        user = User.query.get(user_id)
        if not user:
            user = User(id=user_id)
            db.session.add(user)
        
        # Check if game exists, create if not
        game = Game.query.get(game_id)
        if not game:
            game = Game(
                id=game_id,
                title=game_name,
                thumbnail=thumbnail
            )
            db.session.add(game)
        
        # Check if subscription already exists
        existing_sub = Subscription.query.filter_by(
            user_id=user_id,
            game_id=game_id
        ).first()
        
        if existing_sub:
            return False  # Already subscribed
        
        # Create new subscription
        subscription = Subscription(
            user_id=user_id,
            game_id=game_id
        )
        db.session.add(subscription)
        db.session.commit()
        
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error adding subscription: {e}")
        return False

def remove_subscription(user_id: int, game_id: str) -> Tuple[bool, str]:
    """
    Remove a game subscription for a user
    
    Args:
        user_id: Telegram user ID
        game_id: Game ID to unsubscribe from
        
    Returns:
        Tuple of (success, game_name)
    """
    try:
        # Find the subscription
        subscription = Subscription.query.filter_by(
            user_id=user_id,
            game_id=game_id
        ).first()
        
        if not subscription:
            return (False, "Unknown Game")
        
        # Get game name before deleting
        game = Game.query.get(game_id)
        game_name = game.title if game else "Unknown Game"
        
        # Delete the subscription
        db.session.delete(subscription)
        db.session.commit()
        
        return (True, game_name)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error removing subscription: {e}")
        return (False, "Error removing subscription")

def get_user_subscriptions(user_id: int) -> Dict[str, Dict[str, Any]]:
    """
    Get all game subscriptions for a user
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        Dictionary with game_id as keys and game info as values
    """
    try:
        # Query subscriptions and related games
        subscriptions = (Subscription.query
                        .filter_by(user_id=user_id)
                        .join(Game)
                        .all())
        
        result = {}
        for sub in subscriptions:
            game_id = sub.game_id
            result[game_id] = {
                'name': sub.game.title,
                'thumbnail': sub.game.thumbnail,
                'subscribed_at': sub.created_at.isoformat()
            }
            
            # Add latest price if available
            latest_price = (PriceRecord.query
                           .filter_by(game_id=game_id)
                           .order_by(PriceRecord.recorded_at.desc())
                           .first())
            if latest_price:
                result[game_id]['price'] = latest_price.price
                result[game_id]['discount_percent'] = latest_price.discount_percent
                result[game_id]['store_id'] = latest_price.store_id
        
        return result
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching user subscriptions: {e}")
        return {}

def get_all_subscriptions() -> Dict[str, List[int]]:
    """
    Get all game subscriptions grouped by game_id
    
    Returns:
        Dictionary with game_id as keys and list of user_ids as values
    """
    try:
        # Query all subscriptions
        subscriptions = Subscription.query.all()
        
        game_subscriptions = {}
        for sub in subscriptions:
            game_id = sub.game_id
            if game_id not in game_subscriptions:
                game_subscriptions[game_id] = []
            game_subscriptions[game_id].append(sub.user_id)
        
        return game_subscriptions
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching all subscriptions: {e}")
        return {}

def get_subscribed_users_for_game(game_id: str) -> List[int]:
    """
    Get all users subscribed to a specific game
    
    Args:
        game_id: Game ID to check
        
    Returns:
        List of user IDs subscribed to the game
    """
    try:
        # Query subscriptions for this game
        subscriptions = Subscription.query.filter_by(game_id=game_id).all()
        return [sub.user_id for sub in subscriptions]
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching subscribers for game: {e}")
        return []

def update_game_price(game_id: str, store_id: str, price: float, discount_percent: int) -> Optional[Dict[str, Any]]:
    """
    Update or add price information for a game
    
    Args:
        game_id: Game ID
        store_id: Store ID
        price: Current price
        discount_percent: Discount percentage
        
    Returns:
        Previous price information or None if no previous info
    """
    try:
        # Check if game exists
        game = Game.query.get(game_id)
        if not game:
            logger.warning(f"Attempted to update price for unknown game: {game_id}")
            return None
        
        # Get the latest price record for this game and store
        previous_record = (PriceRecord.query
                          .filter_by(game_id=game_id, store_id=store_id)
                          .order_by(PriceRecord.recorded_at.desc())
                          .first())
        
        # Create a new price record
        price_record = PriceRecord(
            game_id=game_id,
            store_id=store_id,
            price=price,
            discount_percent=discount_percent
        )
        db.session.add(price_record)
        db.session.commit()
        
        # Return previous price data if it exists
        if previous_record:
            return {
                'price': previous_record.price,
                'discount_percent': previous_record.discount_percent,
                'updated_at': previous_record.recorded_at.isoformat()
            }
        return None
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error updating game price: {e}")
        return None

def add_or_update_store(store_id: str, name: str, logo: str = None) -> bool:
    """
    Add or update a store in the database
    
    Args:
        store_id: Store ID
        name: Store name
        logo: Optional URL to store logo
        
    Returns:
        True if successful
    """
    try:
        store = Store.query.get(store_id)
        if store:
            # Update existing store
            store.name = name
            if logo:
                store.logo = logo
        else:
            # Create new store
            store = Store(
                id=store_id,
                name=name,
                logo=logo
            )
            db.session.add(store)
        
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error adding/updating store: {e}")
        return False

def update_user_info(user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> bool:
    """
    Update user information in the database
    
    Args:
        user_id: Telegram user ID
        username: Optional username
        first_name: Optional first name
        last_name: Optional last name
        
    Returns:
        True if successful
    """
    try:
        user = User.query.get(user_id)
        if user:
            # Update existing user
            if username is not None:
                user.username = username
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name
        else:
            # Create new user
            user = User(
                id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            db.session.add(user)
        
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error updating user info: {e}")
        return False
