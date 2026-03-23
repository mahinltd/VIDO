# ©2026 VIDO Mahin Ltd develop by (Tanvir)

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)

class CacheStore:
    def __init__(self, ttl_minutes: int = 120):
        """
        Initializes the in-memory cache store.
        ttl_minutes: Time-to-live for cache items (default 2 hours).
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.lock = asyncio.Lock() # Thread-safe lock for async operations

    async def get(self, url: str, format_type: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an item from the cache if it exists and has not expired.
        """
        cache_key = f"{url}_{format_type}"
        
        async with self.lock:
            if cache_key in self.cache:
                item = self.cache[cache_key]
                if datetime.utcnow() < item['expires_at']:
                    logger.info(f"⚡ Cache HIT for: {cache_key}")
                    return item['data']
                else:
                    # Item has expired, remove it from memory
                    logger.info(f"⏳ Cache EXPIRED for: {cache_key}")
                    del self.cache[cache_key]
            
        return None

    async def set(self, url: str, format_type: str, data: Dict[str, Any]):
        """
        Store an item in the cache with the defined expiration time.
        """
        cache_key = f"{url}_{format_type}"
        expires_at = datetime.utcnow() + self.ttl
        
        async with self.lock:
            self.cache[cache_key] = {
                'data': data,
                'expires_at': expires_at
            }
            logger.info(f"💾 Cache SET for: {cache_key} (Expires in {self.ttl.total_seconds() / 60} mins)")

# Create a global instance of the cache to be used across the application
media_cache = CacheStore(ttl_minutes=120)