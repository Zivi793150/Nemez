import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set
from mongodb_manager import mongodb
from scrapers import ScraperManager
from notifications import send_apartment_notification
from config import Config
from datetime import time as dtime

logger = logging.getLogger(__name__)

class ApartmentMonitor:
    """Monitor for new apartments"""
    
    def __init__(self):
        self.db = mongodb
        self.scraper_manager = ScraperManager()
        self.known_apartment_ids: Set[str] = set()
        self.is_running = False
        self.monitoring_task = None
        # Adaptive job queue for cities (concurrent workers)
        self.jobs_queue: asyncio.Queue = asyncio.Queue()
        self.worker_tasks: List[asyncio.Task] = []
        # Throttle notifications per user
        self._user_last_notify_ts = {}
        # Per-cycle notification caps per user
        self._cycle_user_sent = {}
    
    async def start_monitoring(self):
        """Start the monitoring process"""
        if self.is_running:
            logger.warning("Monitoring is already running")
            return
        
        self.is_running = True
        logger.info("Starting apartment monitoring...")
        
        # Load known apartment IDs
        await self._load_known_apartments()
        
        # Start workers - more workers for faster processing
        worker_count = max(4, min(10, Config.MAX_WORKERS))  # Use config value
        for _ in range(worker_count):
            self.worker_tasks.append(asyncio.create_task(self._worker_loop()))
        # Start monitoring loop (enqueues city jobs)
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self):
        """Stop the monitoring process"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        # stop workers
        for _ in self.worker_tasks:
            try:
                self.jobs_queue.put_nowait(None)  # sentinel
            except Exception:
                pass
        for t in self.worker_tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass
        
        logger.info("Apartment monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Reset per-cycle counters before a new enqueue wave
                self._cycle_user_sent = {}
                await self._enqueue_city_jobs()
                # Adaptive interval: quiet hours vs normal
                now = datetime.now()
                is_quiet = self._is_quiet_hours(now)
                interval = Config.CHECK_INTERVAL_QUIET if is_quiet else Config.CHECK_INTERVAL_NORMAL
                
                # For critical hours (9-18), check more frequently
                if 9 <= now.hour <= 18:
                    interval = min(interval, 30)  # Max 30 seconds during business hours
                
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _load_known_apartments(self):
        """Load known apartment IDs from database"""
        try:
            # Get all apartment IDs from database
            known_ids = await self.db.get_known_apartment_ids()
            self.known_apartment_ids = known_ids
            logger.info(f"Loaded {len(self.known_apartment_ids)} known apartment IDs")
        except Exception as e:
            logger.error(f"Error loading known apartments: {e}")
    
    async def _enqueue_city_jobs(self):
        """Build list of cities from users and enqueue jobs for workers"""
        try:
            # Get users with active subscriptions
            users = await self.db.get_users_with_active_subscriptions()
            
            if not users:
                logger.debug("No users with active subscriptions")
                return
            
            # Get unique cities from user filters
            cities_to_search = set()
            for user in users:
                user_filter = await self.db.get_user_filter(user['telegram_id'])
                if user_filter and user_filter.get('city'):
                    cities_to_search.add(user_filter['city'])
                else:
                    # If user has no city filter, use default
                    cities_to_search.add(Config.DEFAULT_FILTERS['city'])
            
            logger.info(f"Searching apartments for cities: {list(cities_to_search)}")
            # enqueue jobs (one per city)
            for city in cities_to_search:
                city_filters = Config.DEFAULT_FILTERS.copy()
                city_filters['city'] = city
                await self.jobs_queue.put({
                    'filters': city_filters,
                    'users': users
                })
                
        except Exception as e:
            logger.error(f"Error enqueuing city jobs: {e}")

    async def _worker_loop(self):
        """Worker: pulls city job, fetches apartments, notifies users"""
        while self.is_running:
            job = await self.jobs_queue.get()
            if job is None:
                # sentinel
                break
            try:
                filters = job['filters']
                users = job['users']
                city = filters.get('city', 'Unknown')
                logger.info(f"[Worker] Fetching city {city}")
                # Fetch and then cap to avoid signature mismatch and floods
                new_apartments = await self.scraper_manager.get_new_apartments(filters, self.known_apartment_ids)
                if not new_apartments:
                    continue
                logger.info(f"[Worker] City {city} returned {len(new_apartments)} new")
                # Hard cap per job to avoid floods
                to_process = new_apartments[:Config.MAX_APARTMENTS_PER_JOB]
                for apartment_data in to_process:
                    try:
                        await self._process_new_apartment(apartment_data, users)
                    except Exception as e:
                        logger.error(f"Process new apartment failed: {e}")
                        continue
            except Exception as e:
                logger.error(f"Worker error: {e}")
            finally:
                self.jobs_queue.task_done()
    
    async def _process_new_apartment(self, apartment_data: Dict, users: List):
        """Process a new apartment and notify users"""
        try:
            # Validate minimal fields
            if not isinstance(apartment_data, dict) or not apartment_data.get('external_id') or not apartment_data.get('source'):
                logger.warning("Skip invalid apartment payload from provider")
                return

            # Save apartment to database
            apartment_id = await self.db.save_apartment(apartment_data)
            
            # Add to known IDs
            apartment_id_str = f"{apartment_data['source']}_{apartment_data['external_id']}"
            self.known_apartment_ids.add(apartment_id_str)
            
            # Notify users with priority system
            notification_tasks = []
            for user in users:
                try:
                    # Check if apartment matches user's filters
                    if await self._matches_user_filters(apartment_data, user):
                        # Create notification task for parallel processing
                        task = asyncio.create_task(self._send_user_notification(user, apartment_data, apartment_id))
                        notification_tasks.append(task)
                        
                except Exception as e:
                    logger.error(f"Error preparing notification for user {user['telegram_id']}: {e}")
                    continue
            
            # Send all notifications in parallel for speed
            if notification_tasks:
                await asyncio.gather(*notification_tasks, return_exceptions=True)
                logger.info(f"Sent {len(notification_tasks)} notifications for apartment {apartment_id}")
                    
        except Exception as e:
            logger.error(f"Error processing new apartment: {e}")
    
    async def _send_user_notification(self, user: Dict, apartment_data: Dict, apartment_id: str):
        """Send notification to a single user"""
        try:
            # Throttle per user to avoid spam bursts
            import time
            throttle_seconds = getattr(Config, 'NOTIFICATION_THROTTLE_SECONDS', 5)
            last = self._user_last_notify_ts.get(user['telegram_id'], 0.0)
            now = time.time()
            wait = throttle_seconds - (now - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._user_last_notify_ts[user['telegram_id']] = time.time()
            # Enforce per-cycle cap
            max_per_cycle = getattr(Config, 'MAX_NOTIFY_PER_CYCLE', 5)
            sent_so_far = self._cycle_user_sent.get(user['telegram_id'], 0)
            if sent_so_far >= max_per_cycle:
                return
            
            # Create notification record
            await self.db.save_notification(user['telegram_id'], apartment_id)
            
            # Send notification
            await send_apartment_notification(user['telegram_id'], apartment_data, user.get('language', 'de'))
            # Increment per-cycle counter
            self._cycle_user_sent[user['telegram_id']] = sent_so_far + 1
            
            logger.info(f"Notified user {user['telegram_id']} about apartment {apartment_id}")
            
        except Exception as e:
            logger.error(f"Error notifying user {user['telegram_id']}: {e}")
    
    async def _matches_user_filters(self, apartment_data: Dict, user: Dict) -> bool:
        """Check if apartment matches user's filters with priority system"""
        try:
            # Get user's filters
            user_filter = await self.db.get_user_filter(user['telegram_id'])
            
            if not user_filter:
                # No filters set, accept all apartments
                return True
            
            # Priority 1: City (most important filter)
            if user_filter.get('city') and apartment_data.get('city'):
                if user_filter['city'].lower() not in apartment_data['city'].lower():
                    return False
            
            # Priority 2: Price range (critical for budget)
            price = apartment_data.get('price', 0)
            if price > 0:  # Only check if price is available
                if user_filter.get('price_min') and price < user_filter['price_min']:
                    return False
                if user_filter.get('price_max') and price > user_filter['price_max']:
                    return False
            
            # Priority 3: Rooms range
            rooms = apartment_data.get('rooms', 0)
            if rooms > 0:  # Only check if rooms info is available
                if user_filter.get('rooms_min') and rooms < user_filter['rooms_min']:
                    return False
                if user_filter.get('rooms_max') and rooms > user_filter['rooms_max']:
                    return False
            
            # Priority 4: Area range (less critical)
            area = apartment_data.get('area', 0)
            if area > 0:  # Only check if area info is available
                if user_filter.get('area_min') and area < user_filter['area_min']:
                    return False
                if user_filter.get('area_max') and area > user_filter['area_max']:
                    return False
            
            # Priority 5: Keywords (bonus filter)
            if user_filter.get('keywords'):
                keywords = user_filter['keywords']
                if isinstance(keywords, str):
                    keywords = keywords.split(',')
                elif isinstance(keywords, list):
                    keywords = keywords
                else:
                    keywords = []
                
                apartment_text = f"{apartment_data.get('title', '')} {apartment_data.get('description', '')}".lower()
                
                # Check if any keyword matches
                keyword_match = False
                for keyword in keywords:
                    if keyword.strip().lower() in apartment_text:
                        keyword_match = True
                        break
                
                # If keywords are specified but none match, still allow (soft filter)
                # This ensures users don't miss apartments due to keyword mismatches
                # return keyword_match  # Uncomment for strict keyword filtering
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking user filters: {e}")
            return True  # Default to accepting if there's an error
    
    def _is_quiet_hours(self, now: datetime) -> bool:
        """Return True if current local time is within quiet hours window."""
        try:
            start = Config.QUIET_HOURS_START
            end = Config.QUIET_HOURS_END
            hour = now.hour
            if start == end:
                return False
            if start < end:
                return start <= hour < end
            # Window crosses midnight
            return hour >= start or hour < end
        except Exception:
            return False

    async def force_check(self):
        """Force a check for new apartments (for testing)"""
        logger.info("Forcing apartment check...")
        await self._check_new_apartments()
    
    async def get_monitoring_status(self) -> Dict:
        """Get monitoring status"""
        return {
            "is_running": self.is_running,
            "known_apartments_count": len(self.known_apartment_ids),
            "last_check": datetime.now().isoformat()
        }

# Global monitor instance
monitor = ApartmentMonitor()

async def start_monitoring_service():
    """Start the monitoring service"""
    await monitor.start_monitoring()

async def stop_monitoring_service():
    """Stop the monitoring service"""
    await monitor.stop_monitoring()

async def get_monitoring_status():
    """Get monitoring status"""
    return await monitor.get_monitoring_status()

async def force_apartment_check():
    """Force a check for new apartments"""
    await monitor.force_check()
