#!/usr/bin/env python3
"""
Cache manager for apartment data to improve performance
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib

logger = logging.getLogger(__name__)

class ApartmentCache:
    """In-memory cache for apartment data"""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default TTL
        self.cache: Dict[str, Dict] = {}
        self.ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()
    
    def _generate_key(self, filters: Dict) -> str:
        """Generate cache key from filters"""
        # Sort filters for consistent keys
        sorted_filters = json.dumps(filters, sort_keys=True)
        return hashlib.md5(sorted_filters.encode()).hexdigest()
    
    async def get(self, filters: Dict) -> Optional[List[Dict]]:
        """Get cached apartments for filters"""
        async with self._lock:
            key = self._generate_key(filters)
            if key in self.cache:
                entry = self.cache[key]
                # Check if cache entry is still valid
                if datetime.now() - entry['timestamp'] < timedelta(seconds=self.ttl_seconds):
                    logger.debug(f"Cache hit for key: {key}")
                    return entry['data']
                else:
                    # Remove expired entry
                    del self.cache[key]
                    logger.debug(f"Cache expired for key: {key}")
            return None
    
    async def set(self, filters: Dict, data: List[Dict]) -> None:
        """Cache apartments for filters"""
        async with self._lock:
            key = self._generate_key(filters)
            self.cache[key] = {
                'data': data,
                'timestamp': datetime.now()
            }
            logger.debug(f"Cached {len(data)} apartments for key: {key}")
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self.cache.clear()
            logger.info("Cache cleared")
    
    async def cleanup_expired(self) -> None:
        """Remove expired cache entries"""
        async with self._lock:
            now = datetime.now()
            expired_keys = []
            for key, entry in self.cache.items():
                if now - entry['timestamp'] >= timedelta(seconds=self.ttl_seconds):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

class ImageCache:
    """Cache for image URLs to avoid re-downloading"""
    
    def __init__(self, ttl_seconds: int = 3600):  # 1 hour default TTL
        self.cache: Dict[str, Dict] = {}
        self.ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()
    
    async def get_image_info(self, url: str) -> Optional[Dict]:
        """Get cached image info"""
        async with self._lock:
            if url in self.cache:
                entry = self.cache[url]
                if datetime.now() - entry['timestamp'] < timedelta(seconds=self.ttl_seconds):
                    return entry['data']
                else:
                    del self.cache[url]
            return None
    
    async def set_image_info(self, url: str, info: Dict) -> None:
        """Cache image info"""
        async with self._lock:
            self.cache[url] = {
                'data': info,
                'timestamp': datetime.now()
            }
    
    async def cleanup_expired(self) -> None:
        """Remove expired image cache entries"""
        async with self._lock:
            now = datetime.now()
            expired_keys = []
            for key, entry in self.cache.items():
                if now - entry['timestamp'] >= timedelta(seconds=self.ttl_seconds):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]

# Global cache instances
apartment_cache = ApartmentCache()
image_cache = ImageCache()

async def cleanup_caches():
    """Periodic cleanup of expired cache entries"""
    while True:
        try:
            await apartment_cache.cleanup_expired()
            await image_cache.cleanup_expired()
            await asyncio.sleep(300)  # Cleanup every 5 minutes
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
            await asyncio.sleep(60)

def get_cache_manager():
    """Get cache manager instance"""
    return apartment_cache
