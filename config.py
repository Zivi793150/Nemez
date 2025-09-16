import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    # Database
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "nemez2_bot")
    
    # Redis for caching
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # API Keys for real estate sites
    IMMOSCOUT24_API_KEY = os.getenv("IMMOSCOUT24_API_KEY")
    IMMOWELT_API_KEY = os.getenv("IMMOWELT_API_KEY")
    ESTATESYNC_API_KEY = os.getenv("ESTATESYNC_API_KEY")

    # Apify
    APIFY_TOKEN = os.getenv("APIFY_TOKEN")
    # Optional: separate token for alternate service mentioned by user
    ALT_SCRAPER_TOKEN = os.getenv("ALT_SCRAPER_TOKEN")
    
    # Apify actor IDs (can be overridden by env if changed)
    APIFY_ACTOR_IMMOSCOUT24 = os.getenv("APIFY_ACTOR_IMMOSCOUT24", "azzouzana~immobilienscout24-de-search-results-scraper-by-search-url")
    APIFY_ACTOR_IMMOWELT = os.getenv("APIFY_ACTOR_IMMOWELT", "azzouzana~immowelt-de-search-results-scraper-by-search-url")
    APIFY_ACTOR_KLEINANZEIGEN = os.getenv("APIFY_ACTOR_KLEINANZEIGEN", "real_spidery~kleinanzeigen-scraper")
    # Optional direct start URL for IS24 actor that requires a search URL input
    IS24_START_URL = os.getenv("IS24_START_URL", "")
    # Optional direct start URL for Immowelt actor (classified-search)
    IMMOWELT_START_URL = os.getenv("IMMOWELT_START_URL", "")
    
    # Alternate service keys (same token for multiple domains per user message)
    ALT_SERVICE_IMMOSCOUT24 = os.getenv("ALT_SERVICE_IMMOSCOUT24", "dcdfdac9b71b7dd11f02ca34f823d40843e2ca87")
    ALT_SERVICE_IMMOWELT = os.getenv("ALT_SERVICE_IMMOWELT", "dcdfdac9b71b7dd11f02ca34f823d40843e2ca87")
    ALT_SERVICE_KLEINANZEIGEN = os.getenv("ALT_SERVICE_KLEINANZEIGEN", "dcdfdac9b71b7dd11f02ca34f823d40843e2ca87")
    
    # AI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    ENABLE_AI_ANALYSIS = os.getenv("ENABLE_AI_ANALYSIS", "true").lower() == "true"
    # Feature flags
    ENABLE_DEMO = os.getenv("ENABLE_DEMO", "false").lower() == "true"
    ENABLE_PUBLIC_OSM = os.getenv("ENABLE_PUBLIC_OSM", "false").lower() == "true"
    ENABLE_PLACEHOLDER_RSS = os.getenv("ENABLE_PLACEHOLDER_RSS", "false").lower() == "true"
    
    # Subscription settings
    SUBSCRIPTION_PRICE = 9.99  # EUR per month
    SUBSCRIPTION_DURATION = 30  # days
    
    # Monitoring settings
    CHECK_INTERVAL = 60  # seconds (legacy, kept for backward compatibility)
    # Adaptive monitoring - optimized for speed
    CHECK_INTERVAL_NORMAL = int(os.getenv("CHECK_INTERVAL_NORMAL", "30"))  # 30 seconds for faster updates
    CHECK_INTERVAL_QUIET = int(os.getenv("CHECK_INTERVAL_QUIET", "300"))   # 5 min ночью
    QUIET_HOURS_START = int(os.getenv("QUIET_HOURS_START", "23"))  # 23:00
    QUIET_HOURS_END = int(os.getenv("QUIET_HOURS_END", "7"))      # 07:00
    MAX_RETRIES = 3
    MAX_PRICE_CAP = int(os.getenv("MAX_PRICE_CAP", "5000"))
    
    # Performance settings for scale
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "6"))  # Number of worker threads
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))  # 5 minutes cache
    IMAGE_CACHE_TTL_SECONDS = int(os.getenv("IMAGE_CACHE_TTL_SECONDS", "3600"))  # 1 hour image cache

    # Apify cost controls
    APIFY_COOLDOWN_SECONDS = int(os.getenv("APIFY_COOLDOWN_SECONDS", "300"))  # 5 min минимум между запусками одного актора
    APIFY_QUIET_SCALING = float(os.getenv("APIFY_QUIET_SCALING", "2.0"))      # в тихие часы умножаем кулдаун
    # Apify sync run (wait and return items directly)
    APIFY_SYNC_RUN = os.getenv("APIFY_SYNC_RUN", "true").lower() == "true"
    # Feature flag to enable/disable Immowelt live actor to avoid wasted runs
    ENABLE_IMMOWELT_LIVE = os.getenv("ENABLE_IMMOWELT_LIVE", "false").lower() == "true"

    # Notification limits
    MAX_NOTIFY_PER_CYCLE = int(os.getenv("MAX_NOTIFY_PER_CYCLE", "8"))  # отправляем не более N объявлений за один цикл пользователю
    MAX_APARTMENTS_PER_JOB = int(os.getenv("MAX_APARTMENTS_PER_JOB", "15"))  # общее число обработанных объявлений на город за итерацию
    NOTIFICATION_THROTTLE_SECONDS = int(os.getenv("NOTIFICATION_THROTTLE_SECONDS", "2"))  # минимальная задержка между уведомлениями пользователю
    
    # Supported languages
    SUPPORTED_LANGUAGES = ["de", "ru", "uk"]
    
    # Default filters
    DEFAULT_FILTERS = {
        "city": "Berlin",
        "price_min": 500,
        "price_max": 1500,
        "rooms_min": 1,
        "rooms_max": 4,
        "area_min": 30,
        "area_max": 120
    }
