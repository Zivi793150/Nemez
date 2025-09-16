import aiohttp
import asyncio
import json
import re
import random
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
from config import Config
import logging
from real_api_system import RealEstateAPI
from cache_manager import apartment_cache

logger = logging.getLogger(__name__)

class ScraperManager:
    """Manager for all scrapers - REAL DATA ONLY"""
    
    def __init__(self):
        self.scrapers = {
            'real_api': RealEstateAPI()
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass
    
    def _blend_by_source(self, apartments: List[Dict], per_source: Dict[str, int], filler_limit: int) -> List[Dict]:
        try:
            chosen: List[Dict] = []
            used_ids = set()
            def pick(src: str, n: int):
                picked = 0
                for a in apartments:
                    if picked >= n:
                        break
                    if not isinstance(a, dict):
                        continue
                    if a.get('source') != src:
                        continue
                    ext = f"{a.get('source')}_{a.get('external_id')}"
                    if ext in used_ids:
                        continue
                    chosen.append(a)
                    used_ids.add(ext)
                    picked += 1
            # Primary quotas
            pick('immowelt', per_source.get('immowelt', 0))
            pick('immobilienscout24', per_source.get('immobilienscout24', 0))
            # Fill remaining with anything (e.g., from DB or the rest)
            remaining = filler_limit
            for a in apartments:
                if remaining <= 0:
                    break
                if not isinstance(a, dict):
                    continue
                ext = f"{a.get('source')}_{a.get('external_id')}"
                if ext in used_ids:
                    continue
                chosen.append(a)
                used_ids.add(ext)
                remaining -= 1
            return chosen
        except Exception:
            return apartments[:filler_limit + sum(per_source.values())]
    
    async def search_all_sites(self, filters: Dict) -> List[Dict]:
        """Search all sites for apartments - REAL DATA ONLY with caching"""
        # Check cache first
        cached_result = await apartment_cache.get(filters)
        if cached_result is not None:
            logger.info(f"Returning {len(cached_result)} apartments from cache")
            return cached_result
        
        all_apartments = []
        
        # Try all real sources in parallel
        tasks = []
        for scraper_name, scraper in self.scrapers.items():
            task = asyncio.create_task(self._search_single_scraper(scraper_name, scraper, filters))
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        for result in results:
            if isinstance(result, list):
                # Keep only valid dict items
                all_apartments.extend([a for a in result if isinstance(a, dict)])
            elif isinstance(result, Exception):
                logger.error(f"Scraper error: {result}")
        
        # Blend: 2 immowelt + 2 is24 + 2 filler
        blended = self._blend_by_source(all_apartments, { 'immowelt': 2, 'immobilienscout24': 2 }, 2)
        
        # Cache the results
        await apartment_cache.set(filters, blended)
        
        logger.info(f"Total REAL apartments found: {len(blended)}")
        return blended
    
    async def _search_single_scraper(self, scraper_name: str, scraper, filters: Dict) -> List[Dict]:
        """Search using a single scraper"""
        try:
            async with scraper:
                apartments = await scraper.search_apartments(filters)
                logger.info(f"Found {len(apartments)} REAL apartments on {scraper_name}")
                return apartments
        except Exception as e:
            logger.error(f"Error searching {scraper_name}: {e}")
            return []
    
    async def get_new_apartments(self, filters: Dict, known_ids: set, limit: Optional[int] = None) -> List[Dict]:
        """Get only new apartments that weren't seen before.
        Optionally limit the number of returned new apartments.
        """
        all_apartments = await self.search_all_sites(filters)
        new_apartments = []
        
        for apartment in all_apartments:
            try:
                if not isinstance(apartment, dict):
                    continue
                src = apartment.get('source')
                ext = apartment.get('external_id')
                if not src or not ext:
                    continue
                apartment_id = f"{src}_{ext}"
                if apartment_id not in known_ids:
                    new_apartments.append(apartment)
            except Exception:
                continue
        
        # Apply optional limit
        if isinstance(limit, int) and limit > 0:
            return new_apartments[:limit]
        return new_apartments
