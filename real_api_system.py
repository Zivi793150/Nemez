#!/usr/bin/env python3
"""
Real API system for apartment search
"""

import aiohttp
import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from config import Config
import re
from apartment_cache import get_cache_manager
# from alternative_scrapers import AlternativeScraper  # Удален

logger = logging.getLogger(__name__)

class RealEstateAPI:
    """Real estate API system"""
    
    def __init__(self):
        self.session = None
        self.estatesync_key = Config.ESTATESYNC_API_KEY
        self.immoscout24_key = Config.IMMOSCOUT24_API_KEY
        self.immowelt_key = Config.IMMOWELT_API_KEY
        self.cache_manager = get_cache_manager()
        # Apify / alternate services
        self.apify_token = Config.APIFY_TOKEN
        self.apify_actor_immoscout24 = Config.APIFY_ACTOR_IMMOSCOUT24
        self.apify_actor_immowelt = Config.APIFY_ACTOR_IMMOWELT
        self.apify_actor_kleinanzeigen = Config.APIFY_ACTOR_KLEINANZEIGEN
        self.alt_service_key_immoscout24 = Config.ALT_SERVICE_IMMOSCOUT24
        self.alt_service_key_immowelt = Config.ALT_SERVICE_IMMOWELT
        self.alt_service_key_kleinanzeigen = Config.ALT_SERVICE_KLEINANZEIGEN
        # Apify per-actor cooldowns
        self._last_run_ts: Dict[str, float] = {}
        
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=60)
        connector = aiohttp.TCPConnector(ssl=False, limit=10)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                'User-Agent': 'Nemez2Bot/1.0',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def search_apartments(self, filters: Dict) -> List[Dict]:
        """Search apartments using all available APIs and scrapers"""
        all_apartments = []

        # ONLY Apify actors (as requested)
        
        # Try Apify actors if token present (only IS24 and Immowelt)
        if self.apify_token:
            try:
                apify_results = await asyncio.gather(
                    self._search_apify_immoscout24(filters),
                    self._search_apify_immowelt(filters),
                    return_exceptions=True
                )
                for res in apify_results:
                    if isinstance(res, list):
                        all_apartments.extend(res)
                    elif isinstance(res, Exception):
                        logger.error(f"Apify search error: {res}")
                
                # Filter out only obviously fake apartments (all three are 0 AND no meaningful content)
                def is_valid_apartment(apt):
                    if not isinstance(apt, dict):
                        return False
                    price = apt.get('price', 0)
                    rooms = apt.get('rooms', 0)
                    area = apt.get('area', 0)
                    title = apt.get('title', '')
                    description = apt.get('description', '')
                    url = apt.get('original_url', '') or apt.get('application_url', '')
                    
                    # Keep apartments with at least some meaningful data
                    return (
                        price > 0 or rooms > 0 or area > 0 or 
                        len(title.strip()) > 10 or len(description.strip()) > 20 or
                        url.strip()
                    )
                
                all_apartments = [apt for apt in all_apartments if is_valid_apartment(apt)]
                
                logger.info(f"Found {len(all_apartments)} total after Apify (IS24 + Immowelt)")
            except Exception as e:
                logger.error(f"Apify error: {e}")

        # Fallback: AlternativeScraper удален, используем только Apify
        if not all_apartments:
            logger.info("AlternativeScraper удален, используем только Apify")

        # Do not use any other fallbacks/demos

        return all_apartments
    
    async def _search_estatesync(self, filters: Dict) -> List[Dict]:
        """Search using EstateSync API"""
        if not self.estatesync_key:
            return []
        
        try:
            # Try different EstateSync endpoints
            endpoints = [
                "https://api.estatesync.io/properties",
                "https://api.estatesync.io/listings",
                "https://api.estatesync.io/search"
            ]
            
            headers = {
                'Authorization': f'Bearer {self.estatesync_key}',
                'Content-Type': 'application/json'
            }
            
            params = {
                'city': filters.get('city', 'Berlin'),
                'type': 'apartment',
                'purpose': 'rent'
            }
            
            if filters.get('price_max'):
                params['price_max'] = filters['price_max']
            if filters.get('rooms_max'):
                params['rooms_max'] = filters['rooms_max']
            
            for endpoint in endpoints:
                try:
                    async with self.session.get(endpoint, headers=headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            apartments = self._parse_estatesync_response(data, filters)
                            if apartments:
                                return apartments
                        elif response.status == 404:
                            continue
                        else:
                            logger.warning(f"EstateSync endpoint {endpoint} returned {response.status}")
                            
                except Exception as e:
                    logger.error(f"Error with EstateSync endpoint {endpoint}: {e}")
                    continue
            
            return []
            
        except Exception as e:
            logger.error(f"Error searching EstateSync: {e}")
            return []
    
    async def _search_immoscout24_api(self, filters: Dict) -> List[Dict]:
        """Search using ImmoScout24 API"""
        if not self.immoscout24_key:
            return []
        
        try:
            url = "https://rest.immobilienscout24.de/restapi/api/search/v1.0/search/region"
            
            headers = {
                'Authorization': f'Bearer {self.immoscout24_key}',
                'Content-Type': 'application/json'
            }
            
            search_params = {
                "realEstateType": "APARTMENT_RENT",
                "publishChannel": "RENT",
                "sorting": "RELEVANCE"
            }
            
            if filters.get('city'):
                search_params["geocodes"] = [{"geocodeId": filters['city'], "type": "CITY"}]
            
            if filters.get('price_min') or filters.get('price_max'):
                search_params["price"] = {}
                if filters.get('price_min'):
                    search_params["price"]["min"] = filters['price_min']
                if filters.get('price_max'):
                    search_params["price"]["max"] = filters['price_max']
            
            if filters.get('rooms_min') or filters.get('rooms_max'):
                search_params["numberOfRooms"] = {}
                if filters.get('rooms_min'):
                    search_params["numberOfRooms"]["min"] = filters['rooms_min']
                if filters.get('rooms_max'):
                    search_params["numberOfRooms"]["max"] = filters['rooms_max']
            
            async with self.session.post(url, json=search_params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_immoscout24_response(data, filters)
                else:
                    logger.warning(f"ImmoScout24 API returned {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching ImmoScout24 API: {e}")
            return []
    
    async def _search_immowelt_api(self, filters: Dict) -> List[Dict]:
        """Search using Immowelt API"""
        if not self.immowelt_key:
            return []
        
        try:
            url = "https://api.immowelt.de/v1/search"
            
            headers = {
                'Authorization': f'Bearer {self.immowelt_key}',
                'Content-Type': 'application/json'
            }
            
            search_params = {
                "propertyType": "apartment",
                "purpose": "rent",
                "location": filters.get('city', 'Berlin')
            }
            
            if filters.get('price_max'):
                search_params['maxPrice'] = filters['price_max']
            if filters.get('rooms_max'):
                search_params['maxRooms'] = filters['rooms_max']
            
            async with self.session.post(url, json=search_params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_immowelt_response(data, filters)
                else:
                    logger.warning(f"Immowelt API returned {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching Immowelt API: {e}")
            return []
    
    async def _search_apify_immoscout24(self, filters: Dict) -> List[Dict]:
        """Search ImmoScout24 via Apify ACTOR (not task)."""
        try:
            if not self._can_run_now('immoscout24') and not filters.get('_bypass_cooldown'):
                logger.info("Apify IS24 cooled down, skip this cycle")
                return []
            # Apify run endpoint
            actor_id = self.apify_actor_immoscout24
            # Prefer explicit start URL if provided (actor expects a search URL list)
            start_url = Config.IS24_START_URL or filters.get('is24_start_url')
            input_payload = {}
            if start_url:
                input_payload = {
                    "startUrl": start_url,  # actor expects string, not array
                    "maxPagesToScrape": 1
                }
            else:
                # Fallback: try to build a generic search URL from filters (may be ignored by actor)
                city = str(filters.get('city', 'Berlin'))
                input_payload = {
                    "startUrl": f"https://www.immobilienscout24.de/Suche/radius/wohnung-mieten?centerofsearchaddress={city}&enteredFrom=result_list",
                    "maxPagesToScrape": 1
                }
            if Config.APIFY_SYNC_RUN:
                items = await self._start_apify_run_sync_get_items(actor_id, input_payload, source_name='immoscout24')
                if items is None:
                    return []
                self._mark_run('immoscout24')
            else:
                run_info = await self._start_apify_run(actor_id, input_payload, source_name='immoscout24')
                if not run_info:
                    return []
                self._mark_run('immoscout24')
                logger.info(f"Apify IS24 run started successfully: {run_info.get('data', {}).get('id', 'unknown')}")
                items = await self._fetch_apify_run_items(run_info)
            logger.info(f"Apify IS24 returned {len(items)} items")
            converted = [self._convert_apify_item(item, 'immobilienscout24', filters) for item in items if item]
            converted = [c for c in converted if isinstance(c, dict) and c is not None]
            # Filter out only obviously fake apartments (all three are 0 AND no meaningful content)
            def is_valid_apartment(apt):
                if not isinstance(apt, dict):
                    return False
                price = apt.get('price', 0)
                rooms = apt.get('rooms', 0)
                area = apt.get('area', 0)
                title = apt.get('title', '')
                description = apt.get('description', '')
                url = apt.get('original_url', '') or apt.get('application_url', '')
                
                # Keep apartments with at least some meaningful data
                return (
                    price > 0 or rooms > 0 or area > 0 or 
                    len(title.strip()) > 10 or len(description.strip()) > 20 or
                    url.strip()
                )
            
            converted = [c for c in converted if is_valid_apartment(c)]
            return converted
        except Exception as e:
            logger.error(f"Apify ImmoScout24 error: {e}")
            return []
    
    async def _search_apify_immowelt(self, filters: Dict) -> List[Dict]:
        """Search Immowelt via Apify ACTOR (not task)."""
        try:
            # Allow disabling Immowelt live by config
            if not getattr(Config, 'ENABLE_IMMOWELT_LIVE', False):
                logger.info("Apify Immowelt disabled by config flag, skipping")
                return []
            if not self._can_run_now('immowelt') and not filters.get('_bypass_cooldown'):
                logger.info("Apify Immowelt cooled down, skip this cycle")
                return []
            actor_id = self.apify_actor_immowelt
            # Prefer a single startUrl provided by env/filters to avoid permutations
            city = str(filters.get('city', 'Berlin'))
            import urllib.parse
            # Prefer explicit classified-search URL compatible with azzouzana actor
            # Source: https://www.immowelt.de/classified-search?... (array required)
            explicit_url = (
                getattr(Config, 'IMMOWELT_START_URL', None) or
                filters.get('immowelt_start_url') or
                None
            )
            if explicit_url:
                # Check if URL is for rent (Rent) or buy (Buy) and fix if needed
                if 'distributionTypes=Buy' in explicit_url or 'distributionTypes=Buy_Auction' in explicit_url:
                    logger.warning(f"Immowelt URL configured for BUY, fixing to RENT: {explicit_url}")
                    # Replace Buy with Rent
                    fixed_url = explicit_url.replace('distributionTypes=Buy,Buy_Auction', 'distributionTypes=Rent')
                    fixed_url = fixed_url.replace('distributionTypes=Buy', 'distributionTypes=Rent')
                    
                    # Do not alter locations; use the site-provided URL as-is
                    explicit_url = fixed_url
                    logger.info(f"Fixed Immowelt URL: {explicit_url}")
                
                input_payload = {
                    "startUrl": explicit_url,
                    "maxPagesToScrape": 1
                }
            else:
                # Build a single classified-search URL matching site parameters from filters
                base_url = "https://www.immowelt.de/classified-search"
                params = ["distributionTypes=Rent", "estateTypes=Apartment"]
                city_key = city.lower().strip()
                # Known location IDs to improve accuracy
                location_ids = {
                    'berlin': 'AD08DE6681', 'hamburg': 'AD08DE6683', 'münchen': 'AD08DE6679', 'muenchen': 'AD08DE6679', 'munich': 'AD08DE6679',
                    'köln': 'AD08DE6748', 'koeln': 'AD08DE6748', 'cologne': 'AD08DE6748', 'frankfurt am main': 'AD08DE6678', 'frankfurt': 'AD08DE6678',
                    'stuttgart': 'AD08DE6691', 'düsseldorf': 'AD08DE6698', 'duesseldorf': 'AD08DE6698', 'dusseldorf': 'AD08DE6698',
                    'leipzig': 'AD08DE6707', 'dortmund': 'AD08DE6696', 'essen': 'AD08DE6700', 'bremen': 'AD08DE6685', 'dresden': 'AD08DE6695'
                }
                loc = location_ids.get(city_key)
                if loc:
                    params.append(f"locations={loc}")
                else:
                    # Use exact city label with umlauts where expected
                    city_label = city
                    if city_key in ['muenchen', 'munich']:
                        city_label = 'München'
                    if city_key in ['koeln', 'cologne']:
                        city_label = 'Köln'
                    if city_key in ['duesseldorf', 'dusseldorf']:
                        city_label = 'Düsseldorf'
                    params.append(f"locations={urllib.parse.quote(city_label)}")
                # Map price/rooms
                if isinstance(filters.get('price_min'), (int, float)):
                    params.append(f"priceMin={int(filters['price_min'])}")
                if isinstance(filters.get('price_max'), (int, float)):
                    params.append(f"priceMax={int(filters['price_max'])}")
                if isinstance(filters.get('rooms_min'), (int, float)):
                    params.append(f"numberOfRoomsMin={int(filters['rooms_min'])}")
                if isinstance(filters.get('rooms_max'), (int, float)):
                    params.append(f"numberOfRoomsMax={int(filters['rooms_max'])}")
                start_url = base_url + "?" + "&".join(params)
                logger.info(f"Immowelt startUrl built from filters: {start_url}")
                # Build relaxed (max-only) URL fallback to mitigate actor sensitivity to min-params
                try:
                    relaxed_params = [p for p in params if not (p.startswith('priceMin=') or p.startswith('numberOfRoomsMin='))]
                    relaxed_url = base_url + "?" + "&".join(relaxed_params)
                    logger.info(f"Immowelt relaxed fallback URL: {relaxed_url}")
                    # Build minimal (location-only) URL as the last resort
                    location_only_params = [p for p in params if p.startswith('distributionTypes=') or p.startswith('estateTypes=') or p.startswith('locations=')]
                    location_only_url = base_url + "?" + "&".join(location_only_params)
                    logger.info(f"Immowelt location-only fallback URL: {location_only_url}")
                    urls_built_from_filters = [start_url, relaxed_url, location_only_url]
                except Exception:
                    urls_built_from_filters = [start_url]
                input_payload = {
                    "startUrl": start_url,
                    "maxPagesToScrape": 1
                }
            
            # Use only the paid/rented actor for Immowelt to avoid 403s
            actors_to_try = [
                "azzouzana~immowelt-de-search-results-scraper-by-search-url",
            ]
            
            logger.info(f"Using Immowelt actor: {actors_to_try[0]}")
            items = []
            
            # Only use the single provided startUrl to avoid API churn
            urls_to_try = [input_payload.get("startUrl")]
            # If we built from filters, try relaxed fallback too
            if 'urls_built_from_filters' in locals():
                urls_to_try = urls_built_from_filters
            
            # Try different actors and URLs
            for actor_idx, current_actor_id in enumerate(actors_to_try):
                logger.info(f"🎭 Trying actor {actor_idx+1}: {current_actor_id}")
                
                for i, url in enumerate(urls_to_try):
                    logger.info(f"🔍 Trying URL approach {i+1} with actor {current_actor_id}: {url}")
                    
                    # Different payload formats for different actors
                    if "azzouzana~immowelt-de-search-results-scraper-by-search-url" in current_actor_id:
                        # This actor expects startUrl as a string per API docs
                        test_payload = {
                            "startUrl": url,
                            "enableDeltaMode": False,
                            "maxPagesToScrape": 1
                        }
                    elif "ecomscrape" in current_actor_id or "real_spidery" in current_actor_id:
                        test_payload = {
                            "startUrls": [url],
                            "maxPagesToScrape": 1
                        }
                    else:
                        test_payload = {
                            "startUrl": url,
                            "maxPagesToScrape": 1,
                            "enableDeltaMode": False
                        }

                    try:
                        max_retries = 3
                        backoffs = [0.5, 1.5, 3.0]
                        last_error = None
                        for attempt in range(1, max_retries + 1):
                            try:
                                if Config.APIFY_SYNC_RUN:
                                    items = await self._start_apify_run_sync_get_items(
                                        current_actor_id, test_payload, source_name='immowelt'
                                    )
                                    logger.info(
                                        f"🔍 Immowelt sync response (attempt {attempt}/{max_retries}) for actor {current_actor_id}, URL {i+1}: {len(items) if items else 0} items"
                                    )
                                else:
                                    run_info = await self._start_apify_run(
                                        current_actor_id, test_payload, source_name='immowelt'
                                    )
                                    if not run_info:
                                        logger.warning(
                                            f"Immowelt run failed to start for actor {current_actor_id}, URL {i+1} (attempt {attempt}/{max_retries})"
                                        )
                                        items = []
                                    else:
                                        items = await self._fetch_apify_run_items(run_info)
                                        logger.info(
                                            f"🔍 Immowelt async response (attempt {attempt}/{max_retries}) for actor {current_actor_id}, URL {i+1}: {len(items) if items else 0} items"
                                        )
                                # Break if got any items
                                if items and len(items) > 0:
                                    break
                            except Exception as e:
                                last_error = e
                                logger.warning(f"Immowelt attempt {attempt}/{max_retries} failed with error: {e}")
                            # Backoff if not last attempt
                            if attempt < max_retries:
                                try:
                                    await asyncio.sleep(backoffs[attempt - 1])
                                except Exception:
                                    pass
                        # If after retries still empty, propagate as empty for this URL
                        if (not items) and last_error:
                            logger.warning(f"❌ Actor {current_actor_id}, URL {i+1} failed after retries: {last_error}")
                    except Exception as e:
                        logger.warning(
                            f"❌ Actor {current_actor_id}, URL {i+1} failed with error: {e}"
                        )
                        continue
                
                if items and len(items) > 0:
                    break
            
            if not items:
                logger.error("❌ All URL approaches failed - no items found")
                return []

            self._mark_run('immowelt')
            logger.info(f"Apify Immowelt returned {len(items)} items")
            if items:
                logger.info(f"Sample Immowelt item: {items[0] if items else 'None'}")
            converted = [self._convert_apify_item(item, 'immowelt', filters) for item in items if item]
            converted = [c for c in converted if isinstance(c, dict) and c is not None]
            logger.info(f"Converted {len(converted)} valid Immowelt apartments")
            # Filter out only obviously fake apartments (all three are 0 AND no meaningful content)
            def is_valid_apartment(apt):
                if not isinstance(apt, dict):
                    return False
                price = apt.get('price', 0)
                rooms = apt.get('rooms', 0)
                area = apt.get('area', 0)
                title = apt.get('title', '')
                description = apt.get('description', '')
                url = apt.get('original_url', '') or apt.get('application_url', '')
                
                # Keep apartments with at least some meaningful data
                return (
                    price > 0 or rooms > 0 or area > 0 or 
                    len(title.strip()) > 10 or len(description.strip()) > 20 or
                    url.strip()
                )
            
            converted = [c for c in converted if is_valid_apartment(c)]
            return converted
        except Exception as e:
            logger.error(f"Apify Immowelt error: {e}")
            return []
    
    async def _search_apify_kleinanzeigen(self, filters: Dict) -> List[Dict]:
        """Search Kleinanzeigen via Apify ACTOR (not task)."""
        try:
            if not self._can_run_now('kleinanzeigen'):
                logger.info("Apify Kleinanzeigen cooled down, skip this cycle")
                return []
            actor_id = self.apify_actor_kleinanzeigen
            city = str(filters.get('city', 'Berlin')).lower()
            start_url = f"https://www.kleinanzeigen.de/s-wohnung-mieten/{city}/k0"
            input_payload = {
                # многие акторы принимают оба варианта; передадим оба
                "searchQuery": filters.get('city', 'Berlin'),
                "maxItems": 30,
                "startUrls": [{"url": start_url}],
            }
            run_info = await self._start_apify_run(actor_id, input_payload, source_name='kleinanzeigen')
            if not run_info:
                return []
            self._mark_run('kleinanzeigen')
            items = await self._fetch_apify_run_items(run_info)
            return [self._convert_apify_item(item, 'kleinanzeigen', filters) for item in items if item]
        except Exception as e:
            logger.error(f"Apify Kleinanzeigen error: {e}")
            return []

    def _can_run_now(self, key: str) -> bool:
        """Respect per-actor cooldowns and quiet-hour scaling to reduce costs."""
        try:
            import time
            now = time.time()
            last = self._last_run_ts.get(key, 0.0)
            base = float(Config.APIFY_COOLDOWN_SECONDS)
            # Quiet hours scaling
            from datetime import datetime
            hour = datetime.now().hour
            start = Config.QUIET_HOURS_START
            end = Config.QUIET_HOURS_END
            quiet = (start < end and start <= hour < end) or (start > end and (hour >= start or hour < end))
            cooldown = base * (Config.APIFY_QUIET_SCALING if quiet else 1.0)
            return (now - last) >= cooldown
        except Exception:
            return True

    def _mark_run(self, key: str) -> None:
        try:
            import time
            self._last_run_ts[key] = time.time()
        except Exception:
            pass

    async def _start_apify_run(self, actor_or_task_id: str, payload: Dict, source_name: str) -> Optional[Dict]:
        """Start Apify run trying ACTOR first, then TASK if actor returns 404.
        Returns run_info dict or None.
        """
        try:
            # Try /acts (username~actor-name) — primary per Apify API
            url_acts = f"https://api.apify.com/v2/acts/{actor_or_task_id}/runs?token={self.apify_token}"
            async with self.session.post(
                url_acts,
                json=payload,
                headers={
                    'Authorization': f'Bearer {self.apify_token}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            ) as resp:
                if resp.status in (200, 201):
                    return await resp.json()
                if resp.status != 404:
                    error_text = await resp.text()
                    logger.warning(f"Apify {source_name} start failed (acts): {resp.status} - {error_text}")
            # Try legacy /actors
            url_actors = f"https://api.apify.com/v2/actors/{actor_or_task_id}/runs?token={self.apify_token}"
            async with self.session.post(
                url_actors,
                json=payload,
                headers={
                    'Authorization': f'Bearer {self.apify_token}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            ) as resp1:
                if resp1.status in (200, 201):
                    return await resp1.json()
                if resp1.status != 404:
                    error_text = await resp1.text()
                    logger.warning(f"Apify {source_name} start failed (actors): {resp1.status} - {error_text}")
            # If still 404, try TASK endpoint
            url_task = f"https://api.apify.com/v2/actor-tasks/{actor_or_task_id}/runs?token={self.apify_token}"
            async with self.session.post(
                url_task,
                json=payload,
                headers={
                    'Authorization': f'Bearer {self.apify_token}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            ) as resp2:
                if resp2.status in (200, 201):
                    return await resp2.json()
                error_text = await resp2.text()
                logger.warning(f"Apify {source_name} start failed (actor-tasks): {resp2.status} - {error_text}")
                return None
        except Exception as e:
            logger.error(f"Apify start run error for {source_name}: {e}")
            return None

    async def _start_apify_run_sync_get_items(self, actor_id: str, payload: Dict, source_name: str) -> Optional[List[Dict]]:
        """Run actor synchronously and return dataset items directly (run-sync-get-dataset-items)."""
        try:
            url = f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items?token={self.apify_token}&format=json&clean=true"
            async with self.session.post(
                url,
                json=payload,
                headers={
                    'Authorization': f'Bearer {self.apify_token}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            ) as resp:
                if resp.status in (200, 201):
                    data = await resp.json(content_type=None)
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict):
                        if 'items' in data and isinstance(data['items'], list):
                            return data['items']
                        return data.get('data') or []
                else:
                    text = await resp.text()
                    logger.warning(f"Apify sync {source_name} failed: {resp.status} - {text[:400]}")
                    return None
        except Exception as e:
            logger.error(f"Apify sync run error for {source_name}: {e}")
            return None

    async def _fetch_apify_run_items(self, run_info: Dict) -> List[Dict]:
        """Poll Apify run until succeeded and return dataset items."""
        try:
            # Try to get datasetId or default dataset URL
            dataset_id = None
            if isinstance(run_info, dict):
                if 'data' in run_info and isinstance(run_info['data'], dict):
                    dataset_id = run_info['data'].get('defaultDatasetId') or run_info['data'].get('datasetId')
                dataset_id = dataset_id or run_info.get('defaultDatasetId') or run_info.get('datasetId')
            # Fallback: if runId available, call run endpoint to fetch dataset id
            if not dataset_id:
                run_id = run_info.get('data', {}).get('id') or run_info.get('id')
                if run_id:
                    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={self.apify_token}"
                    for _ in range(60):  # poll up to ~2 minutes
                        async with self.session.get(
                            status_url,
                            headers={
                                'Authorization': f'Bearer {self.apify_token}',
                                'Accept': 'application/json'
                            }
                        ) as sresp:
                            data = await sresp.json()
                            status = data.get('data', {}).get('status') or data.get('status')
                            dataset_id = data.get('data', {}).get('defaultDatasetId') or data.get('defaultDatasetId')
                            logger.info(f"Run status: {status}, dataset_id: {dataset_id}")
                            if status in ['SUCCEEDED', 'FAILED', 'TIMED-OUT', 'ABORTED']:
                                break
                            await asyncio.sleep(2)
                
            if not dataset_id:
                return []
            # Fetch items
            items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?clean=true&token={self.apify_token}"
            logger.info(f"Fetching items from dataset {dataset_id}")
            async with self.session.get(
                items_url,
                headers={
                    'Authorization': f'Bearer {self.apify_token}',
                    'Accept': 'application/json'
                }
            ) as iresp:
                if iresp.status != 200:
                    logger.warning(f"Apify items fetch failed: {iresp.status}")
                    return []
                try:
                    items = await iresp.json()
                    logger.info(f"Raw items response: {len(items) if isinstance(items, list) else 'not a list'}")
                except Exception:
                    text = await iresp.text()
                    logger.error(f"Failed to parse Apify items JSON, response: {text[:200]}...")
                    try:
                        items = json.loads(text)
                    except Exception:
                        logger.error("Failed to parse Apify items")
                        return []
            if isinstance(items, list):
                logger.info(f"Returning {len(items)} items from dataset")
                return items
            logger.warning(f"Items is not a list: {type(items)}")
            return []
        except Exception as e:
            logger.error(f"Apify fetch items error: {e}")
            return []

    def _convert_apify_item(self, item: Dict, source: str, filters: Dict) -> Optional[Dict]:
        """Normalize Apify item to our apartment schema."""
        try:
            if not isinstance(item, dict):
                return None
            city = filters.get('city', 'Berlin')
            title = item.get('title') or item.get('name') or f"Квартира в {city}"
            # Try multiple description fields commonly used by Apify actors
            description = (
                item.get('description') or item.get('text') or item.get('descriptionText') or
                item.get('shortDescription') or item.get('summary') or item.get('teaser') or
                item.get('teaserText') or ""
            )
            
            # Special handling for new Immowelt format
            if source == 'immowelt' and 'mainDescription' in item:
                main_desc = item.get('mainDescription', {})
                if isinstance(main_desc, dict):
                    desc_text = main_desc.get('description') or main_desc.get('headline') or ""
                    if desc_text and len(desc_text) > len(description):
                        description = desc_text
                        logger.info(f"Found Immowelt description: {desc_text[:100]}...")
            # helpers
            def pick_nested(obj, keys):
                try:
                    if obj is None:
                        return None
                    if isinstance(obj, dict):
                        for k in keys:
                            if k in obj and obj[k] not in (None, ""):
                                return obj[k]
                        for v in obj.values():
                            r = pick_nested(v, keys)
                            if r is not None:
                                return r
                    if isinstance(obj, list):
                        for v in obj:
                            r = pick_nested(v, keys)
                            if r is not None:
                                return r
                except Exception:
                    return None
                return None
            def to_float(v):
                try:
                    if v is None:
                        return None
                    if isinstance(v, (int, float)):
                        return float(v)
                    if isinstance(v, str):
                        import re
                        m = re.search(r"([0-9][0-9\.,\s]*)", v)
                        if m:
                            return float(m.group(1).replace(".", "").replace(" ", "").replace(",", "."))
                except Exception:
                    return None
                return None

            price = None
            # Try multiple price fields with more comprehensive search
            price_fields = [
                'price', 'rent', 'priceValue', 'totalPrice', 'coldRent', 'totalRent', 
                'rentPerMonth', 'priceMonthly', 'baseRent', 'netRent', 'grossRent',
                'warmRent', 'coldRent', 'rentPrice', 'monthlyRent', 'rentalPrice',
                'miete', 'kaltmiete', 'warmmiete', 'gesamtmiete', 'price_text'
            ]
            
            # Special handling for new Immowelt format
            if source == 'immowelt' and 'hardFacts' in item:
                hard_facts = item.get('hardFacts', {})
                if 'price' in hard_facts:
                    price_data = hard_facts['price']
                    if isinstance(price_data, dict):
                        price = to_float(price_data.get('value')) or to_float(price_data.get('formatted'))
                        if price and price > 0:
                            logger.info(f"Found Immowelt price: {price}€ from hardFacts")
                
                # Also try to get price from keyfacts array
                if (price is None or price == 0.0) and 'keyfacts' in hard_facts:
                    keyfacts = hard_facts.get('keyfacts', [])
                    for fact in keyfacts:
                        if isinstance(fact, str) and '€' in fact:
                            price = to_float(fact)
                            if price and price > 0:
                                logger.info(f"Found Immowelt price: {price}€ from keyfacts")
                                break
                
                # Try to get price from rawData
                if (price is None or price == 0.0) and 'rawData' in item:
                    raw_data = item.get('rawData', {})
                    if 'price' in raw_data:
                        price = to_float(raw_data['price'])
                        if price and price > 0:
                            logger.info(f"Found Immowelt price: {price}€ from rawData")
            
            for key in price_fields:
                if key in item and item[key] is not None:
                    price = to_float(item[key]) or to_float(pick_nested(item[key], ['value', 'amount', 'text']))
                    if price is not None and price > 0:
                        break
            
            # Try nested price search
            if price is None or price == 0.0:
                price = to_float(pick_nested(item, price_fields + ['amount', 'value']))
            # Try in generic attributes arrays
            if (price is None or price == 0.0) and isinstance(item.get('attributes'), list):
                for attr in item['attributes']:
                    try:
                        if not isinstance(attr, dict):
                            continue
                        key = str(attr.get('key') or attr.get('name') or '').lower()
                        if any(k in key for k in ['price', 'miete', 'kaltmiete', 'warmmiete']):
                            price = to_float(attr.get('value') or attr.get('text'))
                            if price and price > 0:
                                break
                    except Exception:
                        continue
            
            # Enhanced fallback: parse price from title/description with more patterns
            if price is None or price == 0.0:
                try:
                    import re
                    text_price = f"{title} {description}"
                    # More comprehensive price patterns
                    patterns = [
                        r"(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d+)?)\s*€",  # 1.500€ or 1,500€
                        r"€\s*(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d+)?)",  # €1.500
                        r"(\d+(?:[\.,]\d+)?)\s*EUR",  # 1500 EUR
                        r"EUR\s*(\d+(?:[\.,]\d+)?)",  # EUR 1500
                        r"(\d+(?:[\.,]\d+)?)\s*евро",  # 1500 евро
                        r"евро\s*(\d+(?:[\.,]\d+)?)",  # евро 1500
                        r"(\d+(?:[\.,]\d+)?)\s*Euro",  # 1500 Euro
                        r"Euro\s*(\d+(?:[\.,]\d+)?)",  # Euro 1500
                        r"(\d+(?:[\.,]\d+)?)\s*DM",    # 1500 DM (old currency)
                        r"(\d+(?:[\.,]\d+)?)\s*Kaltmiete",  # 1500 Kaltmiete
                        r"(\d+(?:[\.,]\d+)?)\s*Warmmiete",  # 1500 Warmmiete
                        r"Kaltmiete:\s*(\d+(?:[\.,]\d+)?)",  # Kaltmiete: 1500
                        r"Warmmiete:\s*(\d+(?:[\.,]\d+)?)",  # Warmmiete: 1500
                        r"(\d+(?:[\.,]\d+)?)\s*€\s*-\s*(\d+(?:[\.,]\d+)?)\s*€",  # 800€ - 1200€ (take first)
                        r"(\d+(?:[\.,]\d+)?)\s*€\s*/\s*Monat",  # 800€ / Monat
                        r"(\d+(?:[\.,]\d+)?)\s*€\s*pro\s*Monat",  # 800€ pro Monat
                        r"(\d+(?:[\.,]\d+)?)\s*€\s*mtl\.",  # 800€ mtl.
                        r"(\d+(?:[\.,]\d+)?)\s*€\s*monatlich",  # 800€ monatlich
                    ]
                    for pattern in patterns:
                        m = re.search(pattern, text_price, re.IGNORECASE)
                        if m:
                            price_str = m.group(1).replace(".", "").replace(",", ".")
                            try:
                                price = float(price_str)
                                if price > 0:
                                    logger.info(f"Parsed price from text: {price}€ from '{text_price[:100]}...'")
                                    break
                            except ValueError:
                                continue
                except Exception:
                    pass
            rooms = None
            # Try multiple room fields with more comprehensive search
            room_fields = [
                'rooms', 'numRooms', 'numberOfRooms', 'roomCount', 'bedrooms',
                'livingRooms', 'totalRooms', 'zimmer', 'anzahlZimmer', 'roomsNum',
                'anzZimmer', 'anzahl-der-zimmer'
            ]
            
            # Special handling for new Immowelt format
            if source == 'immowelt' and 'hardFacts' in item:
                hard_facts = item.get('hardFacts', {})
                if 'facts' in hard_facts:
                    for fact in hard_facts['facts']:
                        if isinstance(fact, dict) and fact.get('type') == 'numberOfRooms':
                            rooms = to_float(fact.get('splitValue'))
                            if rooms and rooms > 0:
                                logger.info(f"Found Immowelt rooms: {rooms} from hardFacts")
                                break
                
                # Also try to get rooms from keyfacts array
                if (rooms is None or rooms == 0.0) and 'keyfacts' in hard_facts:
                    keyfacts = hard_facts.get('keyfacts', [])
                    for fact in keyfacts:
                        if isinstance(fact, str) and ('Zimmer' in fact or 'Zi.' in fact):
                            rooms = to_float(fact)
                            if rooms and rooms > 0:
                                logger.info(f"Found Immowelt rooms: {rooms} from keyfacts")
                                break
                
                # Try to get rooms from rawData
                if (rooms is None or rooms == 0.0) and 'rawData' in item:
                    raw_data = item.get('rawData', {})
                    if 'nbroom' in raw_data:
                        rooms = to_float(raw_data['nbroom'])
                        if rooms and rooms > 0:
                            logger.info(f"Found Immowelt rooms: {rooms} from rawData")
            
            for key in room_fields:
                if key in item and item[key] is not None:
                    rooms = to_float(item[key])
                    if rooms is not None and rooms > 0:
                        break
            
            # Try nested room search
            if rooms is None or rooms == 0.0:
                rooms = to_float(pick_nested(item, room_fields))
            # Try attributes arrays
            if (rooms is None or rooms == 0.0) and isinstance(item.get('attributes'), list):
                for attr in item['attributes']:
                    try:
                        if not isinstance(attr, dict):
                            continue
                        key = str(attr.get('key') or attr.get('name') or '').lower()
                        if any(k in key for k in ['zimmer', 'rooms']):
                            rooms = to_float(attr.get('value') or attr.get('text'))
                            if rooms and rooms > 0:
                                break
                    except Exception:
                        continue
            
            # Enhanced fallback: parse rooms from title/description with more patterns
            if rooms is None or rooms == 0.0:
                try:
                    import re
                    text_rd = f"{title} {description}"
                    # More comprehensive room patterns
                    patterns = [
                        r"(\d+(?:[\.,]\d+)?)\s*(?:Zimmer|Zi\.|Zi|комнат|комнаты|комната|rooms|room)",
                        r"(?:Zimmer|Zi\.|Zi|комнат|комнаты|комната|rooms|room)\s*(\d+(?:[\.,]\d+)?)",
                        r"(\d+(?:[\.,]\d+)?)\s*Zimmer\s*Wohnung",  # 2 Zimmer Wohnung
                        r"(\d+(?:[\.,]\d+)?)\s*Zimmer\s*Apartment",  # 2 Zimmer Apartment
                        r"(\d+(?:[\.,]\d+)?)\s*Zimmer\s*Wohnung",  # 2 Zimmer Wohnung
                        r"(\d+(?:[\.,]\d+)?)\s*Zimmer\s*Wohnung",  # 2 Zimmer Wohnung
                        r"(\d+(?:[\.,]\d+)?)\s*Zimmer\s*Wohnung",  # 2 Zimmer Wohnung
                        r"(\d+(?:[\.,]\d+)?)\s*Zimmer",  # 1,5 Zimmer
                        r"(\d+(?:[\.,]\d+)?)\s*Zi\.",  # 1,5 Zi.
                        r"(\d+(?:[\.,]\d+)?)\s*Zi",  # 1,5 Zi
                    ]
                    for pattern in patterns:
                        m = re.search(pattern, text_rd, re.IGNORECASE)
                        if m:
                            try:
                                rooms = float(m.group(1).replace(",", "."))
                                if rooms > 0:
                                    logger.info(f"Parsed rooms from text: {rooms} from '{text_rd[:100]}...'")
                                    break
                            except ValueError:
                                continue
                except Exception:
                    rooms = None
            area = None
            # Try multiple area fields with more comprehensive search
            area_fields = [
                'area', 'livingSpace', 'livingArea', 'size', 'squareMeters', 'floorArea',
                'totalArea', 'usableArea', 'wohnflaeche', 'wohnfläche', 'flaeche', 'fläche', 'qm'
            ]
            
            # Special handling for new Immowelt format
            if source == 'immowelt' and 'hardFacts' in item:
                hard_facts = item.get('hardFacts', {})
                if 'facts' in hard_facts:
                    for fact in hard_facts['facts']:
                        if isinstance(fact, dict) and fact.get('type') == 'livingSpace':
                            area = to_float(fact.get('splitValue'))
                            if area and area > 0:
                                logger.info(f"Found Immowelt area: {area}m² from hardFacts")
                                break
                
                # Also try to get area from keyfacts array
                if (area is None or area == 0.0) and 'keyfacts' in hard_facts:
                    keyfacts = hard_facts.get('keyfacts', [])
                    for fact in keyfacts:
                        if isinstance(fact, str) and ('m²' in fact or 'qm' in fact):
                            area = to_float(fact)
                            if area and area > 0:
                                logger.info(f"Found Immowelt area: {area}m² from keyfacts")
                                break
                
                # Try to get area from rawData
                if (area is None or area == 0.0) and 'rawData' in item:
                    raw_data = item.get('rawData', {})
                    if 'surface' in raw_data:
                        surface = raw_data['surface']
                        if isinstance(surface, dict) and 'main' in surface:
                            area = to_float(surface['main'])
                            if area and area > 0:
                                logger.info(f"Found Immowelt area: {area}m² from rawData")
            
            for key in area_fields:
                if key in item and item[key] is not None:
                    area = to_float(item[key])
                    if area is not None and area > 0:
                        break
            
            # Try nested area search
            if area is None or area == 0.0:
                area = to_float(pick_nested(item, area_fields))
            # Try attributes arrays
            if (area is None or area == 0.0) and isinstance(item.get('attributes'), list):
                for attr in item['attributes']:
                    try:
                        if not isinstance(attr, dict):
                            continue
                        key = str(attr.get('key') or attr.get('name') or '').lower()
                        if any(k in key for k in ['wohnfläche', 'wohnflaeche', 'fläche', 'flaeche', 'qm', 'm²', 'm2']):
                            area = to_float(attr.get('value') or attr.get('text'))
                            if area and area > 0:
                                break
                    except Exception:
                        continue
            
            # Enhanced fallback: parse area from title/description with more patterns
            if area is None or area == 0.0:
                try:
                    import re
                    text_ad = f"{title} {description}"
                    # More comprehensive area patterns
                    patterns = [
                        r"(\d+(?:[\.,]\d+)?)\s*m²",  # 50 m²
                        r"(\d+(?:[\.,]\d+)?)\s*qm",  # 50 qm
                        r"(\d+(?:[\.,]\d+)?)\s*кв\.?\s?м",  # 50 кв.м
                        r"(\d+(?:[\.,]\d+)?)\s*m\^2",  # 50 m^2
                        r"(\d+(?:[\.,]\d+)?)\s*квадрат",  # 50 квадрат
                        r"(\d+(?:[\.,]\d+)?)\s*Wohnfläche",  # 50 Wohnfläche
                        r"(\d+(?:[\.,]\d+)?)\s*Wohnflaeche",  # 50 Wohnflaeche
                        r"(\d+(?:[\.,]\d+)?)\s*Fläche",  # 50 Fläche
                        r"(\d+(?:[\.,]\d+)?)\s*Flaeche",  # 50 Flaeche
                        r"Wohnfläche:\s*(\d+(?:[\.,]\d+)?)",  # Wohnfläche: 50
                        r"Fläche:\s*(\d+(?:[\.,]\d+)?)",  # Fläche: 50
                        r"(\d+(?:[\.,]\d+)?)\s*m²",  # 40 m² (duplicate for emphasis)
                    ]
                    for pattern in patterns:
                        m = re.search(pattern, text_ad, re.IGNORECASE)
                        if m:
                            try:
                                area = float(m.group(1).replace(",", "."))
                                if area > 0:
                                    logger.info(f"Parsed area from text: {area}m² from '{text_ad[:100]}...'")
                                    break
                            except ValueError:
                                continue
                except Exception:
                    area = None
            address = item.get('address') or {}
            if isinstance(address, str):
                address = { 'full': address }
            
            # Special handling for new Immowelt format
            if source == 'immowelt' and 'location' in item:
                location = item.get('location', {})
                if 'address' in location and isinstance(location['address'], dict):
                    immowelt_city = location['address'].get('city')
                    if immowelt_city:
                        city = immowelt_city
                        logger.info(f"Found Immowelt city: {city}")
            
            city_name = address.get('city') or item.get('city') or city
            
            # Filter by city if specified in filters
            if 'city' in filters:
                filter_city = str(filters['city']).lower()
                apartment_city = str(city_name).lower()
                
                # More flexible city matching
                city_matches = (
                    filter_city in apartment_city or 
                    apartment_city in filter_city or
                    # Handle common city name variations
                    (filter_city == 'köln' and apartment_city in ['köln', 'koeln', 'cologne']) or
                    (filter_city == 'koeln' and apartment_city in ['köln', 'koeln', 'cologne']) or
                    (filter_city == 'cologne' and apartment_city in ['köln', 'koeln', 'cologne']) or
                    (filter_city == 'berlin' and apartment_city == 'berlin') or
                    (filter_city == 'hamburg' and apartment_city == 'hamburg')
                )
                
                if not city_matches:
                    logger.info(f"Filtering out apartment from {city_name} (looking for {filters['city']})")
                    # Temporarily disable city filtering for Immowelt to see what cities we get
                    if source == 'immowelt':
                        logger.info(f"🚨 TEMPORARILY ALLOWING Immowelt apartment from {city_name} for debugging")
                        # Don't return None, continue processing
                    else:
                        return None
            
            district = (
                item.get('district') or item.get('neighborhood') or item.get('quarter') or
                address.get('district') or address.get('suburb') or address.get('county') or ''
            )
            street = address.get('street') or ''
            postal_code = address.get('postalCode') or address.get('zip') or ''
            # Try multiple possible url fields
            original_url = (
                item.get('applicationUrl') or item.get('adUrl') or item.get('detailUrl') or
                item.get('url') or item.get('link') or item.get('shareLink') or
                pick_nested(item, ['applicationUrl','adUrl','detailUrl','url','link','shareLink']) or ''
            )
            # Construct IS24 URL from id if missing
            if (not original_url) and source in ('immobilienscout24', 'is24'):
                listing_id = (
                    item.get('listingId') or item.get('adId') or item.get('id') or
                    pick_nested(item, ['listingId','adId','id'])
                )
                try:
                    if listing_id:
                        original_url = f"https://www.immobilienscout24.de/expose/{listing_id}"
                except Exception:
                    pass
            # Enhanced image extraction
            images = []
            
            # Special handling for new Immowelt format
            if source == 'immowelt' and 'gallery' in item:
                gallery = item.get('gallery', {})
                if 'images' in gallery and isinstance(gallery['images'], list):
                    for img in gallery['images']:
                        if isinstance(img, dict) and 'url' in img:
                            img_url = img['url']
                            if img_url and img_url.startswith('http'):
                                images.append(img_url)
                                logger.info(f"Found Immowelt image: {img_url[:50]}...")
            
            # Try multiple image fields
            image_fields = [
                'images', 'imageUrls', 'photos', 'gallery', 'pictures', 
                'media', 'attachments', 'imageList', 'photoUrls'
            ]
            
            for field in image_fields:
                if field in item and item[field]:
                    field_data = item[field]
                    if isinstance(field_data, list):
                        images.extend(field_data)
                    elif isinstance(field_data, str):
                        images.append(field_data)
                    elif isinstance(field_data, dict):
                        # Handle nested image objects
                        if 'url' in field_data:
                            images.append(field_data['url'])
                        elif 'src' in field_data:
                            images.append(field_data['src'])
                        elif 'href' in field_data:
                            images.append(field_data['href'])
            
            # Try nested image search
            nested_images = pick_nested(item, image_fields)
            if nested_images:
                if isinstance(nested_images, list):
                    images.extend(nested_images)
                elif isinstance(nested_images, str):
                    images.append(nested_images)
            
            # Normalize base for protocol-relative/relative URLs
            def _normalize_url(u: str) -> str:
                try:
                    if not isinstance(u, str):
                        return u
                    u = u.strip()
                    if not u:
                        return u
                    # Prefer original_url as base
                    base = original_url or ''
                    import re
                    m = re.match(r'^(https?:)//([^/]+)', base)
                    scheme = m.group(1) if m else 'https:'
                    host = m.group(2) if m else ''
                    if u.startswith('//'):
                        return f"{scheme}{u}"
                    if u.startswith('/') and host:
                        return f"{scheme}//{host}{u}"
                    return u
                except Exception:
                    return u

            # Clean and validate images
            valid_images = []
            for img in images:
                if isinstance(img, str):
                    nu = _normalize_url(img)
                    if isinstance(nu, str) and (nu.startswith('http://') or nu.startswith('https://')):
                        valid_images.append(nu)
                elif isinstance(img, dict):
                    for key in ['url', 'src', 'href', 'link']:
                        if key in img and isinstance(img[key], str):
                            nu = _normalize_url(img[key])
                            if isinstance(nu, str) and (nu.startswith('http://') or nu.startswith('https://')):
                                valid_images.append(nu)
                                break
            
            # Remove duplicates and limit to 10 images
            images = list(dict.fromkeys(valid_images))[:10]
            # Set default values for missing data, but don't discard apartments
            if price is None or price <= 0:
                price = 0.0
            if rooms is None or rooms <= 0:
                rooms = 0.0
            if area is None or area <= 0:
                area = 0.0
            
            # Only skip apartments with obviously fake data (all three are 0 AND no meaningful content)
            # Allow apartments with at least some meaningful data
            has_meaningful_content = (
                (price > 0) or (rooms > 0) or (area > 0) or 
                len(title.strip()) > 10 or len(description.strip()) > 20 or
                original_url.strip()
            )
            
            if not has_meaningful_content:
                return None
            # Build stable external_id using sha1 of (source + canonical url + listing id)
            try:
                import hashlib
                base_id = str(original_url or '') + '|' + str(item.get('id') or item.get('listingId') or '')
                stable_hash = hashlib.sha1((source + '|' + base_id).encode('utf-8')).hexdigest()[:20]
                external_id = f"apify_{source}_{stable_hash}"
            except Exception:
                external_id = f"apify_{source}_{hash(title + original_url)}"
            return {
                'external_id': external_id,
                'source': source,
                'title': title,
                'description': description,
                'price': price,
                'price_type': 'rent',
                'city': city_name,
                'district': district or '',
                'street': street,
                'postal_code': postal_code,
                'rooms': rooms if rooms is not None else 0.0,
                'area': area if area is not None else 0.0,
                'floor': None,
                'total_floors': None,
                'property_type': 'apartment',
                'features': json.dumps([]),
                'images': json.dumps(images),
                'contact_info': json.dumps({}),
                'original_url': original_url,
                'application_url': original_url,
                'additional_info': json.dumps(item)
            }
        except Exception as e:
            logger.error(f"Apify convert item error: {e}")
            return None

    async def _search_alternative_sources(self, filters: Dict) -> List[Dict]:
        """Search alternative sources when APIs are not available"""
        try:
            # Try public real estate APIs
            apartments = await self._search_public_apis(filters)
            if apartments:
                return apartments
            
            # Try RSS feeds
            apartments = await self._search_rss_feeds(filters)
            if apartments:
                return apartments
            
            return []
            
        except Exception as e:
            logger.error(f"Error searching alternative sources: {e}")
            return []
    
    async def _search_public_apis(self, filters: Dict) -> List[Dict]:
        """Search public real estate APIs"""
        try:
            if not Config.ENABLE_PUBLIC_OSM:
                return []
            # Example: OpenStreetMap Overpass API for real estate data
            city = filters.get('city', 'Berlin')
            
            # Overpass query for real estate
            query = f"""
            [out:json][timeout:25];
            area[name="{city}"][admin_level=8]->.searchArea;
            (
              way["building"="apartments"](area.searchArea);
              way["building"="residential"](area.searchArea);
            );
            out body;
            >;
            out skel qt;
            """
            
            url = "https://overpass-api.de/api/interpreter"
            
            async with self.session.post(url, data=query) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_osm_response(data, filters)
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching public APIs: {e}")
            return []
    
    async def _search_rss_feeds(self, filters: Dict) -> List[Dict]:
        """Search RSS feeds for real estate listings"""
        try:
            if not Config.ENABLE_PLACEHOLDER_RSS:
                return []
            # Example RSS feeds (these would need to be real RSS feeds)
            rss_urls = [
                f"https://www.immobilienscout24.de/rss/{filters.get('city', 'Berlin').lower()}/wohnung-mieten.xml",
                f"https://www.immowelt.de/rss/{filters.get('city', 'Berlin').lower()}/wohnungen/mieten.xml"
            ]
            
            apartments = []
            for url in rss_urls:
                try:
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            content = await response.text()
                            # Parse RSS content
                            parsed = self._parse_rss_content(content, filters)
                            apartments.extend(parsed)
                except Exception as e:
                    logger.error(f"Error with RSS feed {url}: {e}")
                    continue
            
            return apartments
            
        except Exception as e:
            logger.error(f"Error searching RSS feeds: {e}")
            return []
    
    def _parse_estatesync_response(self, data: Dict, filters: Dict) -> List[Dict]:
        """Parse EstateSync API response"""
        apartments = []
        
        try:
            # Handle different response structures
            properties = []
            if isinstance(data, list):
                properties = data
            elif isinstance(data, dict):
                if 'data' in data:
                    properties = data['data']
                elif 'properties' in data:
                    properties = data['properties']
                elif 'listings' in data:
                    properties = data['listings']
                elif 'results' in data:
                    properties = data['results']
            
            city_from_filters = filters.get('city', 'Berlin')
            
            for prop in properties:
                try:
                    apartment = self._convert_estatesync_property(prop, city_from_filters)
                    if apartment:
                        apartments.append(apartment)
                except Exception as e:
                    logger.error(f"Error converting EstateSync property: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing EstateSync response: {e}")
            
        return apartments
    
    def _convert_estatesync_property(self, prop: Dict, city: str) -> Optional[Dict]:
        """Convert EstateSync property to our format"""
        try:
            # Extract basic info
            title = prop.get('title', f'Квартира в {city}')
            description = prop.get('description', '')
            
            # Extract price
            price = 0.0
            if 'rent' in prop:
                price = float(prop['rent'])
            elif 'price' in prop:
                price = float(prop['price'])
            elif 'fields' in prop and 'rent' in prop['fields']:
                price = float(prop['fields']['rent'])
            
            # Extract rooms
            rooms = 2.0
            if 'rooms' in prop:
                rooms = float(prop['rooms'])
            elif 'fields' in prop and 'rooms' in prop['fields']:
                rooms = float(prop['fields']['rooms'])
            
            # Extract area
            area = 50.0
            if 'area' in prop:
                area = float(prop['area'])
            elif 'fields' in prop and 'area' in prop['fields']:
                area = float(prop['fields']['area'])
            
            # Extract address
            address = prop.get('address', {})
            if isinstance(address, dict):
                city_name = address.get('city', city)
                street = address.get('street', '')
                postal_code = address.get('postalCode', '')
            else:
                city_name = city
                street = ''
                postal_code = ''
            
            # Extract URL
            original_url = prop.get('url', '')
            if not original_url and 'id' in prop:
                original_url = f"https://estatesync.io/property/{prop['id']}"
            
            # Extract images
            images = []
            if 'images' in prop:
                images = prop['images']
            elif 'media' in prop:
                images = prop['media']
            
            return {
                'external_id': f"estatesync_{prop.get('id', hash(title))}",
                'source': 'estatesync',
                'title': title,
                'description': description,
                'price': price,
                'price_type': 'rent',
                'city': city_name,
                'district': '',
                'street': street,
                'postal_code': postal_code,
                'rooms': rooms,
                'area': area,
                'floor': None,
                'total_floors': None,
                'property_type': 'apartment',
                'features': json.dumps([]),
                'images': json.dumps(images),
                'contact_info': json.dumps({}),
                'original_url': original_url,
                'application_url': original_url,
                'additional_info': json.dumps(prop)
            }
            
        except Exception as e:
            logger.error(f"Error converting EstateSync property: {e}")
            return None
    
    def _parse_immoscout24_response(self, data: Dict, filters: Dict) -> List[Dict]:
        """Parse ImmoScout24 API response"""
        apartments = []
        
        try:
            results = data.get('resultlist.resultlist', {}).get('resultlistEntries', [])
            city_from_filters = filters.get('city', 'Berlin')
            
            for result in results:
                try:
                    apartment = self._convert_immoscout24_property(result, city_from_filters)
                    if apartment:
                        apartments.append(apartment)
                except Exception as e:
                    logger.error(f"Error converting ImmoScout24 property: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing ImmoScout24 response: {e}")
            
        return apartments
    
    def _convert_immoscout24_property(self, prop: Dict, city: str) -> Optional[Dict]:
        """Convert ImmoScout24 property to our format"""
        try:
            # Extract basic info
            title = prop.get('title', f'Квартира в {city}')
            description = prop.get('description', '')
            
            # Extract price
            price = 0.0
            if 'price' in prop:
                price = float(prop['price'].get('value', 0))
            
            # Extract rooms
            rooms = 2.0
            if 'numberOfRooms' in prop:
                rooms = float(prop['numberOfRooms'])
            
            # Extract area
            area = 50.0
            if 'livingSpace' in prop:
                area = float(prop['livingSpace'])
            
            # Extract address
            address = prop.get('address', {})
            city_name = address.get('city', city)
            street = address.get('street', '')
            postal_code = address.get('postalCode', '')
            
            # Extract URL
            original_url = f"https://www.immobilienscout24.de/expose/{prop.get('@id', '')}"
            
            # Extract images
            images = []
            if 'galleryAttachments' in prop:
                for attachment in prop['galleryAttachments']:
                    if 'href' in attachment:
                        images.append(attachment['href'])
            
            return {
                'external_id': f"is24_api_{prop.get('@id', hash(title))}",
                'source': 'immobilienscout24',
                'title': title,
                'description': description,
                'price': price,
                'price_type': 'rent',
                'city': city_name,
                'district': '',
                'street': street,
                'postal_code': postal_code,
                'rooms': rooms,
                'area': area,
                'floor': None,
                'total_floors': None,
                'property_type': 'apartment',
                'features': json.dumps([]),
                'images': json.dumps(images),
                'contact_info': json.dumps({}),
                'original_url': original_url,
                'application_url': original_url,
                'additional_info': json.dumps(prop)
            }
            
        except Exception as e:
            logger.error(f"Error converting ImmoScout24 property: {e}")
            return None
    
    def _parse_immowelt_response(self, data: Dict, filters: Dict) -> List[Dict]:
        """Parse Immowelt API response"""
        apartments = []
        
        try:
            results = data.get('results', [])
            city_from_filters = filters.get('city', 'Berlin')
            
            for result in results:
                try:
                    apartment = self._convert_immowelt_property(result, city_from_filters)
                    if apartment:
                        apartments.append(apartment)
                except Exception as e:
                    logger.error(f"Error converting Immowelt property: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing Immowelt response: {e}")
            
        return apartments
    
    def _convert_immowelt_property(self, prop: Dict, city: str) -> Optional[Dict]:
        """Convert Immowelt property to our format"""
        try:
            # Extract basic info
            title = prop.get('title', f'Квартира в {city}')
            description = prop.get('description', '')
            
            # Extract price
            price = 0.0
            if 'price' in prop:
                price = float(prop['price'])
            
            # Extract rooms
            rooms = 2.0
            if 'rooms' in prop:
                rooms = float(prop['rooms'])
            
            # Extract area
            area = 50.0
            if 'area' in prop:
                area = float(prop['area'])
            
            # Extract address
            address = prop.get('address', {})
            city_name = address.get('city', city)
            street = address.get('street', '')
            postal_code = address.get('postalCode', '')
            
            # Extract URL
            original_url = prop.get('url', '')
            
            # Extract images
            images = prop.get('images', [])
            
            return {
                'external_id': f"immowelt_api_{prop.get('id', hash(title))}",
                'source': 'immowelt',
                'title': title,
                'description': description,
                'price': price,
                'price_type': 'rent',
                'city': city_name,
                'district': '',
                'street': street,
                'postal_code': postal_code,
                'rooms': rooms,
                'area': area,
                'floor': None,
                'total_floors': None,
                'property_type': 'apartment',
                'features': json.dumps([]),
                'images': json.dumps(images),
                'contact_info': json.dumps({}),
                'original_url': original_url,
                'application_url': original_url,
                'additional_info': json.dumps(prop)
            }
            
        except Exception as e:
            logger.error(f"Error converting Immowelt property: {e}")
            return None
    
    def _parse_osm_response(self, data: Dict, filters: Dict) -> List[Dict]:
        """Parse OpenStreetMap response"""
        apartments = []
        
        try:
            elements = data.get('elements', [])
            city_from_filters = filters.get('city', 'Berlin')
            
            for element in elements:
                try:
                    if element.get('type') == 'way' and 'tags' in element:
                        tags = element['tags']
                        if tags.get('building') in ['apartments', 'residential']:
                            apartment = self._convert_osm_property(element, city_from_filters)
                            if apartment:
                                apartments.append(apartment)
                except Exception as e:
                    logger.error(f"Error converting OSM property: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing OSM response: {e}")
            
        return apartments
    
    def _convert_osm_property(self, element: Dict, city: str) -> Optional[Dict]:
        """Convert OSM property to our format"""
        try:
            tags = element.get('tags', {})
            
            title = f"Квартира в {city}"
            if 'name' in tags:
                title = tags['name']
            
            # Extract address info
            street = tags.get('addr:street', '')
            postal_code = tags.get('addr:postcode', '')
            
            return {
                'external_id': f"osm_{element.get('id', hash(title))}",
                'source': 'openstreetmap',
                'title': title,
                'description': f"Квартира в {city}",
                'price': 0.0,  # OSM doesn't have price info
                'price_type': 'rent',
                'city': city,
                'district': '',
                'street': street,
                'postal_code': postal_code,
                'rooms': 2.0,
                'area': 50.0,
                'floor': None,
                'total_floors': None,
                'property_type': 'apartment',
                'features': json.dumps([]),
                'images': json.dumps([]),
                'contact_info': json.dumps({}),
                'original_url': f"https://www.openstreetmap.org/way/{element.get('id', '')}",
                'application_url': f"https://www.openstreetmap.org/way/{element.get('id', '')}",
                'additional_info': json.dumps(tags)
            }
            
        except Exception as e:
            logger.error(f"Error converting OSM property: {e}")
            return None
    
    def _parse_rss_content(self, content: str, filters: Dict) -> List[Dict]:
        """Parse RSS content"""
        apartments = []
        
        try:
            # Simple RSS parsing (in real implementation, use proper RSS parser)
            if '<item>' in content:
                items = content.split('<item>')[1:]  # Skip first split
                
                for item in items:
                    try:
                        apartment = self._convert_rss_item(item, filters)
                        if apartment:
                            apartments.append(apartment)
                    except Exception as e:
                        logger.error(f"Error converting RSS item: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error parsing RSS content: {e}")
            
        return apartments
    
    def _convert_rss_item(self, item: str, filters: Dict) -> Optional[Dict]:
        """Convert RSS item to our format"""
        try:
            # Extract title
            title_match = re.search(r'<title>(.*?)</title>', item)
            title = title_match.group(1) if title_match else f"Квартира в {filters.get('city', 'Berlin')}"
            
            # Extract description
            desc_match = re.search(r'<description>(.*?)</description>', item)
            description = desc_match.group(1) if desc_match else ""
            
            # Extract link
            link_match = re.search(r'<link>(.*?)</link>', item)
            original_url = link_match.group(1) if link_match else ""
            
            # Extract price from description
            price = 0.0
            if description:
                price_match = re.search(r'(\d+(?:,\d+)?)\s*€', description)
                if price_match:
                    price = float(price_match.group(1).replace(',', '.'))
            
            return {
                'external_id': f"rss_{hash(title)}",
                'source': 'rss',
                'title': title,
                'description': description,
                'price': price,
                'price_type': 'rent',
                'city': filters.get('city', 'Berlin'),
                'district': '',
                'street': '',
                'postal_code': '',
                'rooms': 2.0,
                'area': 50.0,
                'floor': None,
                'total_floors': None,
                'property_type': 'apartment',
                'features': json.dumps([]),
                'images': json.dumps([]),
                'contact_info': json.dumps({}),
                'original_url': original_url,
                'application_url': original_url,
                'additional_info': json.dumps({})
            }
            
        except Exception as e:
            logger.error(f"Error converting RSS item: {e}")
            return None
