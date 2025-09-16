import logging
import asyncio
from typing import Dict, List, Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from config import Config
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MongoDBManager:
    """MongoDB manager for bot data"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.users_collection = None
        self.subscriptions_collection = None
        self.user_filters_collection = None
        self.apartments_collection = None
        self.notifications_collection = None
    
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(Config.MONGODB_URI)
            self.db = self.client[Config.MONGODB_DATABASE]
            
            # Initialize collections
            self.users_collection = self.db.users
            self.subscriptions_collection = self.db.subscriptions
            self.user_filters_collection = self.db.user_filters
            self.apartments_collection = self.db.apartments
            self.notifications_collection = self.db.notifications
            
            # Create indexes
            await self._create_indexes()
            
            logger.info(f"Connected to MongoDB: {Config.MONGODB_URI}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def _create_indexes(self):
        """Create database indexes"""
        try:
            # Users collection indexes
            await self.users_collection.create_index("telegram_id", unique=True)
            
            # Subscriptions collection indexes
            await self.subscriptions_collection.create_index("user_id")
            await self.subscriptions_collection.create_index("expires_at")
            
            # User filters collection indexes
            await self.user_filters_collection.create_index("user_id", unique=True)
            
            # Apartments collection indexes
            await self.apartments_collection.create_index("external_id", unique=True)
            await self.apartments_collection.create_index("city")
            await self.apartments_collection.create_index("price")
            await self.apartments_collection.create_index("rooms")
            await self.apartments_collection.create_index("created_at")
            
            # Notifications collection indexes
            await self.notifications_collection.create_index("user_id")
            await self.notifications_collection.create_index("apartment_id")
            await self.notifications_collection.create_index("created_at")
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    # User management
    async def create_user(self, telegram_id: int, username: str = None, 
                         first_name: str = None, last_name: str = None, 
                         language: str = "de") -> Dict:
        """Create a new user"""
        try:
            user_data = {
                "telegram_id": telegram_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "language": language,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await self.users_collection.insert_one(user_data)
            user_data["_id"] = result.inserted_id
            
            logger.info(f"Created user: {telegram_id}")
            return user_data
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    async def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by telegram ID"""
        try:
            user = await self.users_collection.find_one({"telegram_id": telegram_id})
            return user
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    async def update_user(self, telegram_id: int, **kwargs) -> bool:
        """Update user data"""
        try:
            kwargs["updated_at"] = datetime.utcnow()
            result = await self.users_collection.update_one(
                {"telegram_id": telegram_id},
                {"$set": kwargs}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    # Subscription management
    async def create_subscription(self, user_id: int, duration_days: int = 30) -> Dict:
        """Create a new subscription"""
        try:
            subscription_data = {
                "user_id": user_id,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=duration_days),
                "status": "active"
            }
            
            result = await self.subscriptions_collection.insert_one(subscription_data)
            subscription_data["_id"] = result.inserted_id
            
            logger.info(f"Created subscription for user: {user_id}")
            return subscription_data
            
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return None
    
    async def get_active_subscription(self, user_id: int) -> Optional[Dict]:
        """Get active subscription for user"""
        try:
            subscription = await self.subscriptions_collection.find_one({
                "user_id": user_id,
                "status": "active",
                "expires_at": {"$gt": datetime.utcnow()}
            })
            return subscription
        except Exception as e:
            logger.error(f"Error getting subscription: {e}")
            return None
    
    # User filters management
    async def save_user_filter(self, user_id: int, filters: Dict) -> bool:
        """Save or update user filters"""
        try:
            filter_data = {
                "user_id": user_id,
                **filters,
                "updated_at": datetime.utcnow()
            }
            
            result = await self.user_filters_collection.update_one(
                {"user_id": user_id},
                {"$set": filter_data},
                upsert=True
            )
            
            logger.info(f"Saved filters for user {user_id}: {filter_data}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving user filters: {e}")
            return False
    
    async def get_user_filter(self, user_id: int) -> Optional[Dict]:
        """Get user filters"""
        try:
            filters = await self.user_filters_collection.find_one({"user_id": user_id})
            logger.info(f"Retrieved filters for user {user_id}: {filters}")
            return filters
        except Exception as e:
            logger.error(f"Error getting user filters: {e}")
            return None
    
    # Apartment management
    async def save_apartment(self, apartment_data: Dict) -> Optional[str]:
        """Save apartment to database"""
        try:
            # Add timestamps
            apartment_data["created_at"] = datetime.utcnow()
            apartment_data["updated_at"] = datetime.utcnow()
            
            # Check if apartment already exists
            existing = await self.apartments_collection.find_one({
                "external_id": apartment_data["external_id"],
                "source": apartment_data["source"]
            })
            
            if existing:
                # Update existing apartment
                result = await self.apartments_collection.update_one(
                    {"_id": existing["_id"]},
                    {"$set": apartment_data}
                )
                apartment_id = str(existing["_id"])
                logger.info(f"Updated apartment: {apartment_id}")
            else:
                # Create new apartment
                result = await self.apartments_collection.insert_one(apartment_data)
                apartment_id = str(result.inserted_id)
                logger.info(f"Saved new apartment: {apartment_id}")
            
            return apartment_id
            
        except Exception as e:
            logger.error(f"Error saving apartment: {e}")
            return None
    
    async def get_apartments_by_filters(self, filters: Dict, limit: int = 10, skip: int = 0) -> List[Dict]:
        """Get apartments matching filters"""
        try:
            query = {}
            
            if filters.get("city"):
                query["city"] = {"$regex": filters["city"], "$options": "i"}
            
            # Apply price bounds with global cap
            if filters.get("price_min") is not None:
                query["price"] = query.get("price", {})
                query["price"]["$gte"] = filters["price_min"]
            
            if filters.get("price_max") is not None:
                query["price"] = query.get("price", {})
                price_max = min(filters["price_max"], Config.MAX_PRICE_CAP)
                query["price"]["$lte"] = price_max
            
            # Only exclude obviously fake price values (negative prices)
            # Allow 0 prices as they might be valid (e.g., "price on request")
            query["price"] = query.get("price", {})
            query["price"]["$gte"] = 0
            
            if filters.get("rooms_min") is not None:
                query["rooms"] = query.get("rooms", {})
                query["rooms"]["$gte"] = filters["rooms_min"]
            
            if filters.get("rooms_max") is not None:
                query["rooms"] = query.get("rooms", {})
                query["rooms"]["$lte"] = filters["rooms_max"]
            
            logger.info(f"MongoDB query: {query}")
            apartments = await self.apartments_collection.find(query).skip(skip).limit(limit).to_list(length=limit)
            
            logger.info(f"Found {len(apartments)} apartments with filters: {filters}")
            return apartments
            
        except Exception as e:
            logger.error(f"Error getting apartments: {e}")
            return []
    
    async def get_all_apartments(self, limit: int = 50) -> List[Dict]:
        """Get all apartments"""
        try:
            apartments = await self.apartments_collection.find().limit(limit).to_list(length=limit)
            return apartments
        except Exception as e:
            logger.error(f"Error getting all apartments: {e}")
            return []
    
    async def get_known_apartment_ids(self) -> set:
        """Get all known apartment external IDs"""
        try:
            cursor = self.apartments_collection.find({}, {"external_id": 1, "source": 1})
            apartments = await cursor.to_list(length=None)
            
            known_ids = set()
            for apt in apartments:
                known_ids.add(f"{apt['source']}_{apt['external_id']}")
            
            return known_ids
            
        except Exception as e:
            logger.error(f"Error getting known apartment IDs: {e}")
            return set()
    
    # Notification management
    async def save_notification(self, user_id: int, apartment_id: str) -> bool:
        """Save notification record"""
        try:
            notification_data = {
                "user_id": user_id,
                "apartment_id": apartment_id,
                "created_at": datetime.utcnow()
            }
            
            await self.notifications_collection.insert_one(notification_data)
            return True
            
        except Exception as e:
            logger.error(f"Error saving notification: {e}")
            return False
    
    async def get_user_notifications(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user notifications"""
        try:
            notifications = await self.notifications_collection.find(
                {"user_id": user_id}
            ).sort("created_at", DESCENDING).limit(limit).to_list(length=limit)
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error getting user notifications: {e}")
            return []
    
    # Additional methods needed by the bot
    async def get_users_with_active_subscriptions(self) -> List[Dict]:
        """Get all users with active subscriptions"""
        try:
            # Get active subscriptions
            active_subscriptions = await self.subscriptions_collection.find({
                "status": "active",
                "expires_at": {"$gt": datetime.utcnow()}
            }).to_list(length=None)
            
            # Get user IDs from subscriptions
            user_ids = [sub["user_id"] for sub in active_subscriptions]
            
            # Get users
            users = await self.users_collection.find({
                "telegram_id": {"$in": user_ids}
            }).to_list(length=None)
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting users with active subscriptions: {e}")
            return []

    async def get_users_with_filters(self) -> List[Dict]:
        """Get all users with their filters for personalized notifications"""
        try:
            # Get all users with active subscriptions
            users = await self.get_users_with_active_subscriptions()
            
            # Get filters for each user
            users_with_filters = []
            for user in users:
                user_id = user["telegram_id"]
                filters = await self.get_user_filter(user_id)
                
                if filters:
                    user_data = {
                        "telegram_id": user_id,
                        "username": user.get("username"),
                        "language": user.get("language", "de"),
                        "filters": filters
                    }
                    users_with_filters.append(user_data)
            
            logger.info(f"Found {len(users_with_filters)} users with filters")
            return users_with_filters
            
        except Exception as e:
            logger.error(f"Error getting users with filters: {e}")
            return []
    
    async def update_user_language(self, telegram_id: int, language: str) -> bool:
        """Update user language"""
        try:
            result = await self.users_collection.update_one(
                {"telegram_id": telegram_id},
                {"$set": {"language": language, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user language: {e}")
            return False

    async def cleanup_old_apartments(self, days_old: int = 30) -> int:
        """Clean up apartments older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            result = await self.apartments_collection.delete_many({
                "created_at": {"$lt": cutoff_date}
            })
            
            deleted_count = result.deleted_count
            logger.info(f"Cleaned up {deleted_count} apartments older than {days_old} days")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old apartments: {e}")
            return 0

# Global MongoDB manager instance
mongodb = MongoDBManager()
