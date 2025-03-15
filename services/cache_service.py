
import redis
import json
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        
    def set_cache(self, key: str, value: Any, expire_seconds: int = 3600) -> bool:
        """Store value in cache"""
        try:
            self.redis_client.setex(key, expire_seconds, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
            
    def get_cache(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
