import os
import logging
import aiohttp
import json
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# In a real-world scenario, you would use actual API keys for these services
# For this example, we'll simulate using the CheapShark API which doesn't require an API key
CHEAPSHARK_API_URL = "https://www.cheapshark.com/api/1.0"

async def search_game(query: str) -> List[Dict[str, Any]]:
    """
    Search for games using the CheapShark API
    
    Args:
        query: The game title to search for
        
    Returns:
        A list of game results with id, title, and thumbnail
    """
    try:
        async with aiohttp.ClientSession() as session:
            search_url = f"{CHEAPSHARK_API_URL}/games?title={query}&limit=10"
            
            async with session.get(search_url) as response:
                if response.status != 200:
                    logger.error(f"API request failed with status {response.status}")
                    return []
                
                data = await response.json()
                
                # Format the response to our standard format
                results = []
                for game in data:
                    results.append({
                        'id': game.get('gameID'),
                        'name': game.get('external'),
                        'thumbnail': game.get('thumb'),
                        'cheapest_price': game.get('cheapest')
                    })
                
                return results
    except Exception as e:
        logger.error(f"Error searching for game: {e}")
        return []

async def get_game_details(game_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific game
    
    Args:
        game_id: The game ID to get details for
        
    Returns:
        A dictionary with game details or None if not found
    """
    try:
        async with aiohttp.ClientSession() as session:
            # First, get the game info
            game_url = f"{CHEAPSHARK_API_URL}/games?id={game_id}"
            
            async with session.get(game_url) as response:
                if response.status != 200:
                    logger.error(f"API request failed with status {response.status}")
                    return None
                
                data = await response.json()
                
                if not data:
                    return None
                
                # Format the response to our standard format
                game_info = {
                    'id': game_id,
                    'name': data.get('info', {}).get('title', 'Unknown Game'),
                    'thumbnail': data.get('info', {}).get('thumb'),
                    'stores': [],
                    'prices': {}
                }
                
                # Process deals information
                for deal in data.get('deals', []):
                    store_id = deal.get('storeID')
                    
                    # Get store name (in a real implementation, you might want to cache this)
                    store_name = await get_store_name(session, store_id)
                    
                    if store_name:
                        game_info['stores'].append(store_name)
                        
                        # Add pricing information
                        current_price = deal.get('price')
                        retail_price = deal.get('retailPrice')
                        
                        try:
                            discount_percent = int(float(deal.get('savings', '0')))
                        except (ValueError, TypeError):
                            discount_percent = 0
                            
                        game_info['prices'][store_name] = {
                            'current': f"${current_price}" if current_price else "Unknown",
                            'original': f"${retail_price}" if retail_price else "Unknown",
                            'discount_percent': discount_percent
                        }
                
                return game_info
    except Exception as e:
        logger.error(f"Error getting game details: {e}")
        return None

async def get_store_name(session: aiohttp.ClientSession, store_id: str) -> Optional[str]:
    """
    Get the store name for a given store ID
    
    Args:
        session: The aiohttp session to use
        store_id: The store ID to look up
        
    Returns:
        The store name or None if not found
    """
    try:
        stores_url = f"{CHEAPSHARK_API_URL}/stores"
        
        async with session.get(stores_url) as response:
            if response.status != 200:
                logger.error(f"API request failed with status {response.status}")
                return None
            
            stores = await response.json()
            
            for store in stores:
                if store.get('storeID') == store_id:
                    return store.get('storeName')
            
            return "Unknown Store"
    except Exception as e:
        logger.error(f"Error getting store name: {e}")
        return "Unknown Store"
