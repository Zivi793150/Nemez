import asyncio
import logging
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.filters import BaseFilter

# Создаем простой текстовый фильтр для callback_query
class TextFilter(BaseFilter):
    def __init__(self, text: str = None, startswith: str = None):
        self.text = text
        self.startswith = startswith
    
    async def __call__(self, callback_query: types.CallbackQuery) -> bool:
        if self.text and callback_query.data == self.text:
            return True
        if self.startswith and callback_query.data.startswith(self.startswith):
            return True
        return False
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode

from config import Config
import json
from mongodb_manager import mongodb
from locales import get_text, format_price_range, format_rooms_range, format_area_range, format_filter_value
from monitor import start_monitoring_service, stop_monitoring_service, get_monitoring_status
from notifications import set_bot_instance, get_apartment_keyboard
from cache_manager import cleanup_caches

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=Config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# MongoDB manager
db = mongodb

# Popular German cities for quick selection
POPULAR_CITIES = [
    "Berlin", "München", "Hamburg", "Köln", "Frankfurt am Main",
    "Stuttgart", "Düsseldorf", "Leipzig", "Dortmund", "Essen",
    "Bremen", "Dresden", "Hannover", "Nürnberg", "Duisburg",
    "Bochum", "Wuppertal", "Bielefeld", "Bonn", "Mannheim"
]

# FSM States
class UserStates(StatesGroup):
    waiting_for_language = State()
    waiting_for_city = State()
    waiting_for_price_min = State()
    waiting_for_price_max = State()
    waiting_for_rooms_min = State()
    waiting_for_rooms_max = State()
    waiting_for_area_min = State()
    waiting_for_area_max = State()
    waiting_for_keywords = State()
    # New states for settings
    waiting_for_settings_price_min = State()
    waiting_for_settings_price_max = State()
    waiting_for_settings_rooms_min = State()
    waiting_for_settings_rooms_max = State()

# Keyboard builders
def get_language_keyboard():
    """Get language selection keyboard"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang_de"))
    builder.add(InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"))
    builder.add(InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_uk"))
    builder.adjust(1)
    return builder.as_markup()

def get_city_selection_keyboard(page=0, language="de"):
    """Get city selection keyboard with pagination - 3-4 cities per page"""
    builder = InlineKeyboardBuilder()
    
    # Show 4 cities per page
    cities_per_page = 4
    start_idx = page * cities_per_page
    end_idx = start_idx + cities_per_page
    current_cities = POPULAR_CITIES[start_idx:end_idx]
    
    # Debug: Log the keyboard creation
    logger.info(f"Creating city keyboard for page {page}: cities {start_idx}-{end_idx}: {current_cities}")
    
    # Add city buttons (1 per row for better visibility)
    for city in current_cities:
        builder.add(InlineKeyboardButton(text=city, callback_data=f"city_{city}"))
    
    # Add navigation buttons (3 buttons: left, back, right)
    nav_row = []
    
    # Previous page button (only if not first page)
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"city_page_{page-1}"))
        logger.info(f"Added previous page button: city_page_{page-1}")
    else:
        # Disabled state for first page
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data="city_page_disabled"))
        logger.info("Added disabled previous page button")
    
    # Back to main menu button
    nav_row.append(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    
    # Next page button (only if not last page)
    if end_idx < len(POPULAR_CITIES):
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"city_page_{page+1}"))
        logger.info(f"Added next page button: city_page_{page+1}")
    else:
        # Disabled state for last page
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data="city_page_disabled"))
        logger.info("Added disabled next page button")
    
    builder.row(*nav_row)
    
    # Add manual input option
    builder.add(InlineKeyboardButton(text="✏️ Ввести город вручную", callback_data="city_manual"))
    
    return builder.as_markup()

def get_main_menu_keyboard(language="de"):
    """Get main menu keyboard"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=get_text("set_filters", language), 
        callback_data="set_filters"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 Статистика", 
        callback_data="stats"
    ))
    builder.add(InlineKeyboardButton(
        text=get_text("settings", language), 
        callback_data="settings"
    ))
    builder.add(InlineKeyboardButton(
        text=get_text("help", language), 
        callback_data="help"
    ))
    builder.adjust(1)
    return builder.as_markup()

def get_subscription_keyboard(language="de"):
    """Get subscription keyboard"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=get_text("pay_subscription", language, price=Config.SUBSCRIPTION_PRICE), 
        callback_data="subscribe"
    ))
    builder.add(InlineKeyboardButton(
        text=get_text("back", language), 
        callback_data="main_menu"
    ))
    builder.adjust(1)
    return builder.as_markup()

def get_price_selection_keyboard(current_price=None, is_min=True, language="de"):
    """Get price selection keyboard with preset values"""
    builder = InlineKeyboardBuilder()
    
    # Preset prices - more realistic for German market
    prices = [300, 500, 800, 1000, 1200, 1500, 1800, 2000, 2500, 3000, 4000, 5000]
    
    # Add price buttons (4 per row for better layout)
    for i in range(0, len(prices), 4):
        row = []
        for j in range(4):
            if i + j < len(prices):
                price = prices[i + j]
                # Highlight current price if set
                button_text = f"✅ {price}€" if current_price == price else f"{price}€"
                row.append(InlineKeyboardButton(
                    text=button_text, 
                    callback_data=f"price_{'min' if is_min else 'max'}_{price}"
                ))
        builder.row(*row)
    
    # Add manual input and back buttons
    builder.add(InlineKeyboardButton(text="✏️ Ввести вручную", callback_data=f"price_manual_{'min' if is_min else 'max'}"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="settings_filters"))
    
    return builder.as_markup()

def get_initial_price_selection_keyboard(is_min=True, language="de"):
    """Get price selection keyboard for initial filter setup"""
    builder = InlineKeyboardBuilder()
    
    # Preset prices - more realistic for German market
    prices = [300, 500, 800, 1000, 1200, 1500, 1800, 2000, 2500, 3000, 4000, 5000]
    
    # Add price buttons (4 per row for better layout)
    for i in range(0, len(prices), 4):
        row = []
        for j in range(4):
            if i + j < len(prices):
                price = prices[i + j]
                row.append(InlineKeyboardButton(
                    text=f"{price}€", 
                    callback_data=f"initial_price_{'min' if is_min else 'max'}_{price}"
                ))
        builder.row(*row)
    
    # Add manual input button
    builder.add(InlineKeyboardButton(text="✏️ Ввести вручную", callback_data=f"initial_price_manual_{'min' if is_min else 'max'}"))
    
    return builder.as_markup()

def get_rooms_selection_keyboard(current_rooms=None, is_min=True, language="de"):
    """Get rooms selection keyboard with preset values"""
    builder = InlineKeyboardBuilder()
    
    # Preset room counts
    rooms = [1, 2, 3, 4]
    
    # Add room buttons (3 per row)
    for i in range(0, len(rooms), 3):
        row = []
        for j in range(3):
            if i + j < len(rooms):
                room = rooms[i + j]
                # Highlight current room count if set
                button_text = f"✅ {room} {'комната' if room == 1 else 'комнаты' if room < 5 else 'комнат'}" if current_rooms == room else f"{room} {'комната' if room == 1 else 'комнаты' if room < 5 else 'комнат'}"
                row.append(InlineKeyboardButton(
                    text=button_text, 
                    callback_data=f"rooms_{'min' if is_min else 'max'}_{room}"
                ))
        builder.row(*row)
    
    # Add manual input and back buttons
    builder.add(InlineKeyboardButton(text="✏️ Ввести вручную", callback_data=f"rooms_manual_{'min' if is_min else 'max'}"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="settings_filters"))
    
    return builder.as_markup()

def get_initial_rooms_selection_keyboard(is_min=True, language="de"):
    """Get rooms selection keyboard for initial filter setup"""
    builder = InlineKeyboardBuilder()
    
    # Preset room counts
    rooms = [1, 2, 3, 4]
    
    # Add room buttons (3 per row)
    for i in range(0, len(rooms), 3):
        row = []
        for j in range(3):
            if i + j < len(rooms):
                room = rooms[i + j]
                row.append(InlineKeyboardButton(
                    text=f"{room} {'комната' if room == 1 else 'комнаты' if room < 5 else 'комнат'}", 
                    callback_data=f"initial_rooms_{'min' if is_min else 'max'}_{room}"
                ))
        builder.row(*row)
    
    # Add manual input button
    builder.add(InlineKeyboardButton(text="✏️ Ввести вручную", callback_data=f"initial_rooms_manual_{'min' if is_min else 'max'}"))
    
    return builder.as_markup()

def get_settings_filters_keyboard(language="de"):
    """Get settings filters keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="💰 Минимальная цена", callback_data="settings_price_min"))
    builder.add(InlineKeyboardButton(text="💰 Максимальная цена", callback_data="settings_price_max"))
    builder.add(InlineKeyboardButton(text="🏠 Минимум комнат", callback_data="settings_rooms_min"))
    builder.add(InlineKeyboardButton(text="🏠 Максимум комнат", callback_data="settings_rooms_max"))
    builder.add(InlineKeyboardButton(text="🔙 Назад в настройки", callback_data="settings"))
    
    builder.adjust(1)
    return builder.as_markup()



# Command handlers
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handle /start command"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        # New user - create record
        user = await db.create_user(
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        logger.info(f"New user registered: {user_id}")
    
    # Send welcome message
    welcome_text = get_welcome_message(user.get('language', 'de'))
    
    await message.answer(
        welcome_text,
        reply_markup=get_subscription_keyboard(user.get('language', 'de')),
        parse_mode=ParseMode.MARKDOWN_V2
    )

@router.message(Command("my_apartments"))
async def cmd_my_apartments(message: types.Message):
    """Show user's available apartments based on their filters"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Пользователь не найден. Используйте /start для регистрации.")
        return
    
    # Check if user has active subscription
    subscription = await db.get_active_subscription(user_id)
    if not subscription:
        await message.answer("❌ У вас нет активной подписки. Используйте /subscribe для активации.")
        return
    
    # Get user's filters
    user_filters = await db.get_user_filter(user_id)
    if not user_filters:
        await message.answer("❌ У вас не настроены фильтры. Используйте /filters для настройки.")
        return
    
    # Show loading message
    loading_msg = await message.answer("🔍 Ищу квартиры по вашим фильтрам...")
    
    try:
        # Get apartments matching user's filters
        apartments = await db.get_apartments_by_filters(user_filters, limit=10)
        
        if not apartments:
            await loading_msg.edit_text("😔 По вашим фильтрам пока нет доступных квартир.\n\n💡 Попробуйте:\n• Расширить диапазон цен\n• Изменить количество комнат\n• Выбрать другой город")
            return
        
        # Create message with apartments
        message_text = f"🏠 **Найдено {len(apartments)} квартир по вашим фильтрам:**\n\n"
        
        for i, apartment in enumerate(apartments[:6], 1):  # Show max 6 (1 from DB + 5 live)
            message_text += f"**{i}. {apartment.get('title', 'Квартира')}**\n"
            message_text += f"📍 {apartment.get('city', 'Не указан')}"
            
            if apartment.get('district'):
                message_text += f", {apartment['district']}"
            message_text += "\n"
            
            message_text += f"💰 {apartment.get('price', 0)}€"
            if apartment.get('deposit'):
                message_text += f" (залог: {apartment['deposit']}€)"
            message_text += "\n"
            
            message_text += f"🏠 {apartment.get('rooms', 0)} комнат • 📏 {apartment.get('area', 0)} м²"
            
            if apartment.get('floor'):
                message_text += f" • 🏢 {apartment['floor']} этаж"
            message_text += "\n"
            
            if apartment.get('heating'):
                message_text += f"🔥 Отопление: {apartment['heating']}\n"
            
            if apartment.get('year_built'):
                message_text += f"📅 Год постройки: {apartment['year_built']}\n"
            
            if apartment.get('description'):
                description = apartment['description'][:150] + "..." if len(apartment['description']) > 150 else apartment['description']
                message_text += f"📝 {description}\n"
            
            if apartment.get('url'):
                message_text += f"🔗 [Посмотреть объявление]({apartment['url']})\n"
            
            message_text += "\n"
        
        if len(apartments) > 6:
            message_text += f"... и еще {len(apartments) - 6} квартир\n"
        
        message_text += "\n💡 Используйте /filters для изменения настроек поиска"
        
        await loading_msg.edit_text(
            message_text,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error showing user apartments: {e}")
        await loading_msg.edit_text("❌ Произошла ошибка при поиске квартир. Попробуйте позже.")

def get_welcome_message(language="de"):
    """Get welcome message with bot description"""
    if language == "ru":
        return f"""🏠 *Добро пожаловать в бот поиска квартир в Германии\\!*

Я помогу вам быстро находить новые квартиры в Германии и получать мгновенные уведомления\\.

*🎯 Что умеет бот:*
• 🔍 Мониторинг всех немецких сайтов недвижимости
• ⚡ Мгновенные уведомления о новых квартирах
• 🎛️ Гибкие фильтры поиска \\(цена, район, комнаты, площадь\\)
• 🌍 Поддержка 3 языков \\(немецкий, русский, украинский\\)
• 💰 Прямая подача заявки на квартиру
• 📱 Удобный интерфейс

*💡 Как это работает:*
1\\. Оформите подписку \\(9\\.99€/месяц\\)
2\\. Настройте фильтры поиска
3\\. Получайте уведомления о новых квартирах
4\\. Подавайте заявки одним кликом

*🚀 Начните прямо сейчас\\!*"""
    
    elif language == "uk":
        return f"""🏠 *Ласкаво просимо до боту пошуку квартир в Німеччині\\!*

Я допоможу вам швидко знаходити нові квартири в Німеччині та отримувати миттєві сповіщення\\.

*🎯 Що вміє бот:*
• 🔍 Моніторинг всіх німецьких сайтів нерухомості
• ⚡ Миттєві сповіщення про нові квартири
• 🎛️ Гнучкі фільтри пошуку \\(ціна, район, кімнати, площа\\)
• 🌍 Підтримка 3 мов \\(німецька, російська, українська\\)
• 💰 Пряма подача заявки на квартиру
• 📱 Зручний інтерфейс

*💡 Як це працює:*
1\\. Оформіть підписку \\(9\\.99€/місяць\\)
2\\. Налаштуйте фільтри пошуку
3\\. Отримуйте сповіщення про нові квартири
4\\. Подавайте заявки одним кліком

*🚀 Почніть прямо зараз\\!*"""
    
    else:  # German
        return f"""🏠 *Willkommen beim Wohnungssuch\\-Bot für Deutschland\\!*

Ich helfe Ihnen dabei, schnell neue Wohnungen in Deutschland zu finden und sofortige Benachrichtigungen zu erhalten\\.

*🎯 Was der Bot kann:*
• 🔍 Überwachung aller deutschen Immobilien\\-Websites
• ⚡ Sofortige Benachrichtigungen über neue Wohnungen
• 🎛️ Flexible Suchfilter \\(Preis, Bezirk, Zimmer, Fläche\\)
• 🌍 Unterstützung für 3 Sprachen \\(Deutsch, Russisch, Ukrainisch\\)
• 💰 Direkte Wohnungsbewerbung
• 📱 Benutzerfreundliche Oberfläche

*💡 So funktioniert es:*
1\\. Abonnement abschließen \\(9\\.99€/Monat\\)
2\\. Suchfilter einstellen
3\\. Benachrichtigungen über neue Wohnungen erhalten
4\\. Bewerbungen mit einem Klick einreichen

*🚀 Starten Sie jetzt\\!*"""

@router.message(Command("language"))
async def cmd_language(message: types.Message):
    """Handle /language command"""
    await message.answer(
        "Выберите язык / Wählen Sie eine Sprache / Виберіть мову:",
        reply_markup=get_language_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Handle /help command"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    language = user.get('language', 'de') if user else "de"
    
    await message.answer(get_text("help_text", language), parse_mode=ParseMode.MARKDOWN_V2)

@router.message(Command("settings"))
async def cmd_settings(message: types.Message):
    """Handle /settings command"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("Пользователь не найден / User not found / Користувача не знайдено", parse_mode=ParseMode.MARKDOWN_V2)
        return
    
    # For now, show subscription info without check
    settings_text = f"""
{get_text("subscription_info", user.get('language', 'de'))}

✅ Подписка активна
📅 Осталось дней: 30
    """
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=get_text("back", user.get('language', 'de')), 
        callback_data="main_menu"
    ))
    
    await message.answer(settings_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN_V2)

@router.message(Command("filters"))
async def cmd_filters(message: types.Message):
    """Handle /filters command"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("Пользователь не найден / User not found / Користувача не знайдено", parse_mode=ParseMode.MARKDOWN_V2)
        return
    
    # Remove subscription check for now
    # subscription = db.get_active_subscription(user.id)
    # if not subscription:
    #     await message.answer(get_text("not_subscribed", user.language), parse_mode=ParseMode.MARKDOWN_V2)
    #     return
    
    # Get current filters from MongoDB
    user_filter = await db.get_user_filter(user['telegram_id'])
    
    if user_filter:
        filters_text = f"""
{get_text("filter_summary", user.get('language', 'de'))}

{get_text("city_filter", user.get('language', 'de'), city=get_text('city', user.get('language', 'de')), city_name=user_filter.get('city', get_text('any', user.get('language', 'de'))))}
{format_price_range(user_filter.get('price_min'), user_filter.get('price_max'), user.get('language', 'de'))}
{format_rooms_range(user_filter.get('rooms_min'), user_filter.get('rooms_max'), user.get('language', 'de'))}
{format_area_range(user_filter.get('area_min'), user_filter.get('area_max'), user.get('language', 'de'))}
🔍 {get_text("keywords", user.get('language', 'de'))}: {', '.join(user_filter.get('keywords', [])) if user_filter.get('keywords') else get_text('any', user.get('language', 'de'))}
        """
    else:
        filters_text = get_text("no_filters", user.get('language', 'de'))
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=get_text("set_filters", user.get('language', 'de')), 
        callback_data="set_filters"
    ))
    builder.add(InlineKeyboardButton(
        text=get_text("back", user.get('language', 'de')), 
        callback_data="main_menu"
    ))
    builder.adjust(1)
    
    await message.answer(filters_text, reply_markup=builder.as_markup())

@router.message(Command("subscription"))
async def cmd_subscription(message: types.Message):
    """Handle /subscription command"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("Пользователь не найден / User not found / Користувача не знайдено", parse_mode=ParseMode.MARKDOWN_V2)
        return
    
    # For now, always show subscription required
    await message.answer(
        get_text("subscription_required", user.get('language', 'de')),
        reply_markup=get_subscription_keyboard(user.get('language', 'de')),
        parse_mode=ParseMode.MARKDOWN_V2
    )

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Handle /stats command"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("Пользователь не найден / User not found / Користувача не знайдено", parse_mode=ParseMode.MARKDOWN_V2)
        return
    
    # Remove subscription check for now
    # subscription = db.get_active_subscription(user.id)
    # if not subscription:
    #     await message.answer(get_text("not_subscribed", user.language), parse_mode=ParseMode.MARKDOWN_V2)
    #     return
    
    # Get statistics from MongoDB
    try:
        # Count apartments found
        total_apartments = await db.apartments_collection.count_documents({})
        
        # Count notifications sent to this user
        user_notifications = await db.notifications_collection.count_documents({
            "user_id": user['telegram_id']
        })
        
        # Get user's filters
        user_filter = await db.get_user_filter(user['telegram_id'])
        
        stats_text = f"""
📊 *Статистика поиска квартир*

🏠 *Всего квартир найдено:* {total_apartments}
🔔 *Уведомлений получено:* {user_notifications}

🎯 *Ваши фильтры:*
"""
        
        if user_filter:
            language = user.get('language', 'de')
            stats_text += f"""
{get_text("city_filter", language, city=get_text("city", language), city_name=user_filter.get('city', get_text("any", language)))}
{format_price_range(user_filter.get('price_min'), user_filter.get('price_max'), language)}
{format_rooms_range(user_filter.get('rooms_min'), user_filter.get('rooms_max'), language)}
{format_area_range(user_filter.get('area_min'), user_filter.get('area_max'), language)}
🔍 {get_text("keywords", language)}: {', '.join(user_filter.get('keywords', [])) if user_filter.get('keywords') else get_text("any", language)}
            """
        else:
            stats_text += get_text("no_filters", user.get('language', 'de'))
        
        stats_text += f"""

⚡ *Мониторинг активен каждую минуту*
🕐 Последняя проверка: {get_monitoring_status()}
        """
        
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(
            text="🔍 Настроить фильтры", 
            callback_data="set_filters"
        ))
        builder.add(InlineKeyboardButton(
            text="🔙 Назад", 
            callback_data="main_menu"
        ))
        builder.adjust(1)
        
        await message.answer(stats_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN_V2)
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await message.answer("Ошибка при получении статистики")

# Callback handlers
@router.callback_query(TextFilter(startswith="lang_"))
async def handle_language_selection(callback: types.CallbackQuery):
    """Handle language selection"""
    language = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    # Update user language
    await db.update_user_language(user_id, language)
    
    # Get welcome message in new language
    welcome_text = get_welcome_message(language)
    
    # Always show subscription button for now
    await callback.message.edit_text(
        welcome_text,
        reply_markup=get_subscription_keyboard(language),
        parse_mode=ParseMode.MARKDOWN_V2
    )

@router.callback_query(TextFilter("main_menu"))
async def handle_main_menu(callback: types.CallbackQuery):
    """Handle main menu"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await callback.answer("User not found")
        return
    
    # Always show subscription button for now
    await callback.message.edit_text(
        get_text("subscription_required", user.get('language', 'de')),
        reply_markup=get_subscription_keyboard(user.get('language', 'de')),
        parse_mode=ParseMode.MARKDOWN_V2
    )

@router.callback_query(TextFilter("stats"))
async def handle_stats(callback: types.CallbackQuery):
    """Handle stats button"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await callback.answer("User not found")
        return
    
    # Remove subscription check for now
    # subscription = db.get_active_subscription(user.id)
    # if not subscription:
    #     await callback.answer("Подписка не активна")
    #     return
    
    # Get statistics
    db_session = db.SessionLocal()
    try:
        from models import Apartment, Notification
        
        # Count apartments found
        total_apartments = db_session.query(Apartment).count()
        
        # Count notifications sent to this user
        user_notifications = db_session.query(Notification).filter(
            Notification.user_id == user.id
        ).count()
        
        # Get user's filters
        from models import UserFilter
        user_filter = db_session.query(UserFilter).filter(
            UserFilter.user_id == user.id
        ).first()
        
        stats_text = f"""
📊 *Статистика поиска квартир*

🏠 *Всего квартир найдено:* {total_apartments}
🔔 *Уведомлений получено:* {user_notifications}

🎯 *Ваши фильтры:*
"""
        
        if user_filter:
            language = user.get('language', 'de')
            stats_text += f"""
{get_text("city_filter", language, city=get_text("city", language), city_name=user_filter.city or get_text("any", language))}
{format_price_range(user_filter.price_min, user_filter.price_max, language)}
{format_rooms_range(user_filter.rooms_min, user_filter.rooms_max, language)}
{format_area_range(user_filter.area_min, user_filter.area_max, language)}
🔍 {get_text("keywords", language)}: {', '.join(user_filter.get_keywords_list()) if user_filter.keywords else get_text("any", language)}
            """
        else:
            stats_text += get_text("no_filters", user.get('language', 'de'))
        
        stats_text += f"""

⚡ *Мониторинг активен каждую минуту*
🕐 Последняя проверка: {get_monitoring_status()}
        """
        
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(
            text="🔍 Настроить фильтры", 
            callback_data="set_filters"
        ))
        builder.add(InlineKeyboardButton(
            text="🔙 Назад", 
            callback_data="main_menu"
        ))
        builder.adjust(1)
        
        await callback.message.edit_text(stats_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN_V2)
        
    finally:
        db_session.close()

@router.callback_query(TextFilter("pay_subscription"))
async def handle_pay_subscription(callback: types.CallbackQuery, state: FSMContext):
    """Handle payment subscription request"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await callback.answer("User not found")
        return
    
    # For now, just create a subscription (in real app, you'd integrate with payment system)
    subscription = await db.create_subscription(user_id)
    
    # Show success message and go directly to basic filters
    success_text = f"""
✅ *{get_text('payment_success', user.get('language', 'de'))}*

🎯 *Теперь настройте базовые фильтры для поиска:*
• Город (обязательно)
• Цена (мин/макс)
• Количество комнат (мин/макс)

        💡 *Совет:* В Германии лучше подавать заявки на все подходящие квартиры\\!
    """
    
    # Go directly to city input
    await callback.message.edit_text(
        success_text + "\n\n" + get_text("enter_city", user.get('language', 'de')),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    
    # Set state for city input
    await state.set_state(UserStates.waiting_for_city)

@router.callback_query(TextFilter("subscribe"))
async def handle_subscribe(callback: types.CallbackQuery):
    """Handle subscription request"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await callback.answer("User not found")
        return
    
    # For now, just create a subscription (in real app, you'd integrate with payment system)
    subscription = await db.create_subscription(user_id)
    
    # Show success message with subscription details
    from datetime import datetime, timedelta
    expires_at = subscription['expires_at']
    days_left = (expires_at - datetime.utcnow()).days
    
    success_text = f"""
✅ *{get_text('payment_success', user.get('language', 'de'))}*

🎯 *Теперь вы можете:*
• Настраивать фильтры поиска
• Получать уведомления о новых квартирах
• Подавать заявки одним кликом

🚀 *Начните с настройки фильтров\\!* 
    """
    
    try:
        await callback.message.edit_text(
            success_text,
            reply_markup=get_main_menu_keyboard(user.get('language', 'de')),
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        # Gracefully handle 'message is not modified' and similar TelegramBadRequest
        err_msg = str(e)
        if "message is not modified" in err_msg.lower():
            # Just update markup to ensure no exception bubbles up
            try:
                await callback.message.edit_reply_markup(
                    reply_markup=get_main_menu_keyboard(user.get('language', 'de'))
                )
            except Exception:
                # Fallback to sending a new message
                await bot.send_message(
                    callback.from_user.id,
                    success_text,
                    reply_markup=get_main_menu_keyboard(user.get('language', 'de')),
                    parse_mode=ParseMode.MARKDOWN_V2
                )
        else:
            # Unknown error: fallback to sending a new message
            await bot.send_message(
                callback.from_user.id,
                success_text,
                reply_markup=get_main_menu_keyboard(user.get('language', 'de')),
                parse_mode=ParseMode.MARKDOWN_V2
            )


@router.callback_query(TextFilter(startswith="ai_recommend_"))
async def handle_ai_recommend(callback: types.CallbackQuery):
    """Recommend 3-5 похожих вариантов через ИИ/правила"""
    try:
        user = await db.get_user(callback.from_user.id)
        if not user:
            await callback.answer("User not found")
            return
        # Parse apartment id
        apt_id = callback.data.replace("ai_recommend_", "")
        from bson import ObjectId
        try:
            obj_id = ObjectId(apt_id)
        except Exception:
            await callback.answer("Apartment not found")
            return
        apt = await db.apartments_collection.find_one({"_id": obj_id})
        if not apt:
            await callback.answer("Apartment not found")
            return
        # Build simple similarity query: same city, +/-20% price, +/-1 rooms
        price = apt.get('price', 0)
        rooms = apt.get('rooms', 0)
        query = {
            "city": {"$regex": apt.get('city', ''), "$options": "i"},
            "price": {"$gte": price * 0.8, "$lte": price * 1.2},
            "rooms": {"$gte": max(0, rooms - 1), "$lte": rooms + 1}
        }
        similar = await db.apartments_collection.find(query).limit(5).to_list(length=5)
        if not similar:
            await callback.answer("Похожих вариантов не найдено")
            return
        # Send short list
        for s in similar:
            text = f"🏠 {s.get('title','Без названия')}\n💰 {s.get('price',0)}€ • 🏠 {s.get('rooms',0)} • 📐 {s.get('area',0)}m²\n{(s.get('description','')[:180] + '...') if s.get('description') else ''}"
            keyboard = get_apartment_keyboard(s, user.get('language','de'))
            await bot.send_message(callback.from_user.id, text, reply_markup=keyboard)
            await asyncio.sleep(0.3)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in AI recommend: {e}")
        await callback.answer("Ошибка подбора")

@router.callback_query(TextFilter("set_filters"))
async def handle_set_filters(callback: types.CallbackQuery, state: FSMContext):
    """Handle set filters request"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await callback.answer("User not found")
        return
    
    # Remove subscription check for now
    # subscription = await db.get_active_subscription(user_id)
    # if not subscription:
    #     await callback.answer(get_text("not_subscribed", user.get('language', 'de')))
    #     return
    
    await state.set_state(UserStates.waiting_for_city)
    await callback.message.edit_text(
        "🏙️ Выберите город для поиска квартир:\n\n"
        "Выберите из списка популярных городов или введите свой:",
        reply_markup=get_city_selection_keyboard(0, user.get('language', 'de'))
    )

@router.callback_query(TextFilter("settings"))
async def handle_settings(callback: types.CallbackQuery):
    """Handle settings request"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await callback.answer("User not found")
        return
    
    # Get user's current filters
    try:
        user_filter = await db.get_user_filters(user.id)
        
        # Show subscription info and current filters
        settings_text = f"""
{get_text("subscription_info", user.language)}

✅ Подписка активна
📅 Осталось дней: 30

🔍 Текущие фильтры:
🏙️ Город: {user_filter.get('city', 'Не указан') if user_filter else 'Не указан'}
💰 Цена: {user_filter.get('price_min', 'Любая') if user_filter else 'Любая'} - {user_filter.get('price_max', 'Любая') if user_filter else 'Любая'}€
🏠 Комнаты: {user_filter.get('rooms_min', 'Любое') if user_filter else 'Любое'} - {user_filter.get('rooms_max', 'Любое') if user_filter else 'Любое'}
        """
        
    except Exception as e:
        logger.error(f"Error getting user filters: {e}")
        settings_text = f"""
{get_text("subscription_info", user.language)}

✅ Подписка активна
📅 Осталось дней: 30
        """
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔧 Редактировать фильтры", callback_data="settings_filters"))
    builder.add(InlineKeyboardButton(
        text=get_text("back", user.language), 
        callback_data="main_menu"
    ))
    
    await callback.message.edit_text(
        settings_text,
        reply_markup=builder.as_markup()
    )

@router.callback_query(TextFilter("help"))
async def handle_help(callback: types.CallbackQuery):
    """Handle help request"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    language = user.get('language', 'de') if user else "de"
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=get_text("back", language), 
        callback_data="main_menu"
    ))
    
    await callback.message.edit_text(
        get_text("help_text", language),
        reply_markup=builder.as_markup()
    )

# City navigation handlers (must come BEFORE city selection handlers)
@router.callback_query(TextFilter(startswith="city_page_"))
async def handle_city_page_navigation(callback: types.CallbackQuery, state: FSMContext):
    """Handle city page navigation"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    # Debug: Log the navigation callback
    logger.info(f"Navigation callback: {callback.data} from user {user_id}")
    
    if callback.data == "city_page_disabled":
        await callback.answer("Это крайняя страница")
        return
    
    try:
        # Extract page number
        page = int(callback.data.replace("city_page_", ""))
        
        # Debug: Log the navigation
        logger.info(f"User {user_id} navigating to city page {page}")
        
        # Update the message with new city selection keyboard
        await callback.message.edit_reply_markup(
            reply_markup=get_city_selection_keyboard(page, user.get('language', 'de'))
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in city page navigation: {e}")
        await callback.answer("Ошибка при переключении страницы")

# Back to main menu handler
@router.callback_query(TextFilter(text="back_to_main"))
async def handle_back_to_main(callback: types.CallbackQuery, state: FSMContext):
    """Handle back to main menu"""
    try:
        # Debug: Log the callback
        logger.info(f"Back to main callback from user {callback.from_user.id}")
        
        # Clear any active state
        await state.clear()
        
        user = await db.get_user(callback.from_user.id)
        if not user:
            await callback.answer("Ошибка: пользователь не найден")
            return
        
        # Show main menu with welcome message
        await callback.message.edit_text(
            get_text("welcome_message", user.get('language', 'de')),
            reply_markup=get_main_menu_keyboard(user.get('language', 'de'))
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error handling back to main: {e}")
        await callback.answer("Ошибка при возврате в главное меню")

# City selection handlers
@router.callback_query(TextFilter(startswith="city_"))
async def handle_city_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle city selection from buttons"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    # Debug: Log the callback
    logger.info(f"City selection callback: {callback.data} from user {user_id}")
    
    # Check if this is a navigation button (should be handled by navigation handler)
    if callback.data.startswith("city_page_"):
        logger.info(f"Navigation callback intercepted by city handler: {callback.data}")
        return
    
    if callback.data == "city_manual":
        # User wants to enter city manually
        logger.info(f"User {user_id} wants to enter city manually")
        await callback.message.edit_text(
            get_text("enter_city", user.get('language', 'de'))
        )
        await state.set_state(UserStates.waiting_for_city)
        return
    
    # Extract city name from callback data
    city = callback.data.replace("city_", "")
    logger.info(f"User {user_id} selected city: {city}")
    
    await state.update_data(city=city)
    await state.set_state(UserStates.waiting_for_price_min)
    
    await callback.message.edit_text(
        f"🏙️ Выбран город: {city}\n\n"
        f"💰 Выберите минимальную цену:",
        reply_markup=get_initial_price_selection_keyboard(is_min=True, language=user.get('language', 'de'))
    )

# Settings filters handlers
@router.callback_query(TextFilter(text="settings_filters"))
async def handle_settings_filters(callback: types.CallbackQuery):
    """Handle settings filters menu"""
    user = await db.get_user(callback.from_user.id)
    
    await callback.message.edit_text(
        "🔧 Настройка фильтров\n\nВыберите параметр для редактирования:",
        reply_markup=get_settings_filters_keyboard(user.get('language', 'de'))
    )

@router.callback_query(TextFilter(text="settings"))
async def handle_back_to_settings(callback: types.CallbackQuery):
    """Handle back to settings menu"""
    user = await db.get_user(callback.from_user.id)
    
    # Get user's current filters
    user_filter = await db.get_user_filter(user['telegram_id'])
    
    # Show subscription info and current filters
    settings_text = f"""
{get_text("subscription_info", user.get('language', 'de'))}

✅ Подписка активна
📅 Осталось дней: 30

🔍 Текущие фильтры:
🏙️ Город: {user_filter.get('city', 'Не указан') if user_filter else 'Не указан'}
💰 Цена: {user_filter.get('price_min', 'Любая') if user_filter else 'Любая'} - {user_filter.get('price_max', 'Любая') if user_filter else 'Любая'}€
🏠 Комнаты: {user_filter.get('rooms_min', 'Любое') if user_filter else 'Любое'} - {user_filter.get('rooms_max', 'Любое') if user_filter else 'Любое'}
    """
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔧 Редактировать фильтры", callback_data="settings_filters"))
    builder.add(InlineKeyboardButton(
        text=get_text("back", user.get('language', 'de')), 
        callback_data="main_menu"
    ))
    
    await callback.message.edit_text(
        settings_text,
        reply_markup=builder.as_markup()
    )



@router.callback_query(TextFilter(text="settings_price_min"))
async def handle_settings_price_min(callback: types.CallbackQuery, state: FSMContext):
    """Handle minimum price settings"""
    user = await db.get_user(callback.from_user.id)
    
    # Get current price_min from user filters
    db_session = db.SessionLocal()
    try:
        from models import UserFilter
        user_filter = db_session.query(UserFilter).filter(UserFilter.user_id == user.id).first()
        current_price = user_filter.price_min if user_filter else None
    finally:
        db_session.close()
    
    await callback.message.edit_text(
        f"💰 Минимальная цена\n\nТекущее значение: {current_price}€" if current_price else "💰 Минимальная цена\n\nВыберите минимальную цену или введите вручную:",
        reply_markup=get_price_selection_keyboard(current_price=current_price, is_min=True, language=user.get('language', 'de'))
    )

@router.callback_query(TextFilter(text="settings_price_max"))
async def handle_settings_price_max(callback: types.CallbackQuery, state: FSMContext):
    """Handle maximum price settings"""
    user = await db.get_user(callback.from_user.id)
    
    # Get current price_max from user filters
    user_filter = await db.get_user_filter(user['telegram_id'])
    current_price = user_filter.get('price_max') if user_filter else None
    
    await callback.message.edit_text(
        f"💰 Максимальная цена\n\nТекущее значение: {current_price}€" if current_price else "💰 Максимальная цена\n\nВыберите максимальную цену или введите вручную:",
        reply_markup=get_price_selection_keyboard(current_price=current_price, is_min=False, language=user.get('language', 'de'))
    )

@router.callback_query(TextFilter(text="settings_rooms_min"))
async def handle_settings_rooms_min(callback: types.CallbackQuery, state: FSMContext):
    """Handle minimum rooms settings"""
    user = await db.get_user(callback.from_user.id)
    
    # Get current rooms_min from user filters
    user_filter = await db.get_user_filter(user['telegram_id'])
    current_rooms = user_filter.get('rooms_min') if user_filter else None
    
    room_text = f"{current_rooms} {'комната' if current_rooms == 1 else 'комнаты' if current_rooms < 5 else 'комнат'}" if current_rooms else None
    
    await callback.message.edit_text(
        f"🏠 Минимум комнат\n\nТекущее значение: {room_text}" if current_rooms else "🏠 Минимум комнат\n\nВыберите минимальное количество комнат или введите вручную:",
        reply_markup=get_rooms_selection_keyboard(current_rooms=current_rooms, is_min=True, language=user.get('language', 'de'))
    )

@router.callback_query(TextFilter(text="settings_rooms_max"))
async def handle_settings_rooms_max(callback: types.CallbackQuery, state: FSMContext):
    """Handle maximum rooms settings"""
    user = await db.get_user(callback.from_user.id)
    
    # Get current rooms_max from user filters
    user_filter = await db.get_user_filter(user['telegram_id'])
    current_rooms = user_filter.get('rooms_max') if user_filter else None
    
    room_text = f"{current_rooms} {'комната' if current_rooms == 1 else 'комнаты' if current_rooms < 5 else 'комнат'}" if current_rooms else None
    
    await callback.message.edit_text(
        f"🏠 Максимум комнат\n\nТекущее значение: {room_text}" if current_rooms else "🏠 Максимум комнат\n\nВыберите максимальное количество комнат или введите вручную:",
        reply_markup=get_rooms_selection_keyboard(current_rooms=current_rooms, is_min=False, language=user.get('language', 'de'))
    )

# Initial price selection handlers
@router.callback_query(TextFilter(startswith="initial_price_"))
async def handle_initial_price_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle initial price selection from buttons"""
    user = await db.get_user(callback.from_user.id)
    
    if callback.data.startswith("initial_price_manual_"):
        is_min = callback.data.endswith("_min")
        await state.set_state(UserStates.waiting_for_price_min if is_min else UserStates.waiting_for_price_max)
        await callback.message.edit_text(
            f"💰 Введите {'минимальную' if is_min else 'максимальную'} цену (€):"
        )
        return
    
    # Extract price from callback data
    parts = callback.data.split("_")
    is_min = parts[2] == "min"
    price = int(parts[3])
    
    # Update only the selected bound, preserve the other if already provided
    if is_min:
        await state.update_data(price_min=price)
    else:
        await state.update_data(price_max=price)
    
    if is_min:
        # Move to max price selection
        await state.set_state(UserStates.waiting_for_price_max)
        await callback.message.edit_text(
            f"💰 Минимальная цена: {price}€\n\n"
            f"💰 Выберите максимальную цену:",
            reply_markup=get_initial_price_selection_keyboard(is_min=False, language=user.get('language', 'de'))
        )
    else:
        # Move to rooms selection
        await state.set_state(UserStates.waiting_for_rooms_min)
        filters_data = await state.get_data()
        language = user.get('language', 'de')
        await callback.message.edit_text(
            f"{format_price_range(filters_data.get('price_min'), filters_data.get('price_max'), language)}\n\n"
            f"🏠 {get_text('enter_rooms_min', language)}",
            reply_markup=get_initial_rooms_selection_keyboard(is_min=True, language=language)
        )

# Initial rooms selection handlers
@router.callback_query(TextFilter(startswith="initial_rooms_"))
async def handle_initial_rooms_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle initial rooms selection from buttons"""
    user = await db.get_user(callback.from_user.id)
    
    if callback.data.startswith("initial_rooms_manual_"):
        is_min = callback.data.endswith("_min")
        await state.set_state(UserStates.waiting_for_rooms_min if is_min else UserStates.waiting_for_rooms_max)
        await callback.message.edit_text(
            f"🏠 Введите {'минимальное' if is_min else 'максимальное'} количество комнат:"
        )
        return
    
    # Extract rooms from callback data
    parts = callback.data.split("_")
    is_min = parts[2] == "min"
    rooms = int(parts[3])
    
    # Update only the selected bound, preserve the other if already provided
    if is_min:
        await state.update_data(rooms_min=rooms)
    else:
        await state.update_data(rooms_max=rooms)
    
    if is_min:
        # Move to max rooms selection
        await state.set_state(UserStates.waiting_for_rooms_max)
        await callback.message.edit_text(
            f"🏠 Минимум комнат: {rooms}\n\n"
            f"🏠 Выберите максимальное количество комнат:",
            reply_markup=get_initial_rooms_selection_keyboard(is_min=False, language=user.get('language', 'de'))
        )
    else:
        # Complete filter setup
        filters_data = await state.get_data()
        
        # Save filters to database
        await db.save_user_filter(user['telegram_id'], filters_data)
        
        await state.clear()
        
        # Create success message with filter summary
        # Format values properly - handle None values correctly
        language = user.get('language', 'de')
        price_min = filters_data.get('price_min')
        price_max = filters_data.get('price_max')
        rooms_min = filters_data.get('rooms_min')
        rooms_max = filters_data.get('rooms_max')
        
        filter_summary = f"""
{get_text("filters_saved", language)}

{get_text("filters_summary", language)}
{get_text("city_filter", language, city=get_text("city", language), city_name=filters_data.get('city', get_text("any", language)))}
{format_price_range(price_min, price_max, language)}
{format_rooms_range(rooms_min, rooms_max, language)}

{get_text("german_market_tip", language)}
        """
        
        await callback.message.edit_text(
            filter_summary,
            reply_markup=get_main_menu_keyboard(user.get('language', 'de'))
        )
        
        # Show available apartments immediately
        await show_available_apartments(callback.from_user.id, filters_data, user.get('language', 'de'))

# Price selection handlers
@router.callback_query(TextFilter(startswith="price_"))
async def handle_price_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle price selection from buttons"""
    user = await db.get_user(callback.from_user.id)
    
    if callback.data.startswith("price_manual_"):
        is_min = callback.data.endswith("_min")
        await state.set_state(UserStates.waiting_for_settings_price_min if is_min else UserStates.waiting_for_settings_price_max)
        await callback.message.edit_text(
            f"💰 Введите {'минимальную' if is_min else 'максимальную'} цену (€):"
        )
        return
    
    # Extract price from callback data
    parts = callback.data.split("_")
    is_min = parts[1] == "min"
    price = int(parts[2])
    
    # Update user filter in MongoDB
    user_filter = await db.get_user_filter(user['telegram_id'])
    if user_filter:
        field = "price_min" if is_min else "price_max"
        await db.user_filters_collection.update_one(
            {"user_id": user['telegram_id']},
            {"$set": {field: price}}
        )
    else:
        filter_data = {"price_min": price} if is_min else {"price_max": price}
        await db.save_user_filter(user['telegram_id'], filter_data)
    
    await callback.answer(f"Цена обновлена: {price}€")
    
    # Update the keyboard to show the new selection
    await callback.message.edit_text(
        f"💰 {'Минимальная' if is_min else 'Максимальная'} цена\n\nТекущее значение: {price}€",
        reply_markup=get_price_selection_keyboard(current_price=price, is_min=is_min, language=user.get('language', 'de'))
    )

# Rooms selection handlers
@router.callback_query(TextFilter(startswith="rooms_"))
async def handle_rooms_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle rooms selection from buttons"""
    user = await db.get_user(callback.from_user.id)
    
    if callback.data.startswith("rooms_manual_"):
        is_min = callback.data.endswith("_min")
        await state.set_state(UserStates.waiting_for_settings_rooms_min if is_min else UserStates.waiting_for_settings_rooms_max)
        await callback.message.edit_text(
            f"🏠 Введите {'минимальное' if is_min else 'максимальное'} количество комнат:"
        )
        return
    
    # Extract rooms from callback data
    parts = callback.data.split("_")
    is_min = parts[1] == "min"
    rooms = int(parts[2])
    
    # Update user filter in MongoDB
    user_filter = await db.get_user_filter(user['telegram_id'])
    if user_filter:
        field = "rooms_min" if is_min else "rooms_max"
        await db.user_filters_collection.update_one(
            {"user_id": user['telegram_id']},
            {"$set": {field: rooms}}
        )
    else:
        filter_data = {"rooms_min": rooms} if is_min else {"rooms_max": rooms}
        await db.save_user_filter(user['telegram_id'], filter_data)
    
    await callback.answer(f"Комнаты обновлены: {rooms}")
    
    # Update the keyboard to show the new selection
    room_text = f"{rooms} {'комната' if rooms == 1 else 'комнаты' if rooms < 5 else 'комнат'}"
    await callback.message.edit_text(
        f"🏠 {'Минимум' if is_min else 'Максимум'} комнат\n\nТекущее значение: {room_text}",
        reply_markup=get_rooms_selection_keyboard(current_rooms=rooms, is_min=is_min, language=user.get('language', 'de'))
    )

# AI Analysis handler
@router.callback_query(TextFilter(startswith="ai_analysis_"))
async def handle_ai_analysis(callback: types.CallbackQuery):
    """Handle AI analysis request"""
    try:
        # Extract apartment ID
        apartment_id = callback.data.replace("ai_analysis_", "")
        
        # Get apartment from MongoDB (convert to ObjectId)
        try:
            from bson import ObjectId
            obj_id = ObjectId(apartment_id)
        except Exception:
            await callback.answer("Квартира не найдена")
            return
        apartment = await db.apartments_collection.find_one({"_id": obj_id})
        
        if not apartment:
            await callback.answer("Квартира не найдена")
            return
        
        # Send AI analysis
        from notifications import send_ai_analysis
        user = await db.get_user(callback.from_user.id)
        await send_ai_analysis(callback.from_user.id, apartment, user.get('language', 'de'))
        
        await callback.answer("AI анализ отправлен!")
        
    except Exception as e:
        logger.error(f"Error in AI analysis: {e}")
        await callback.answer("Ошибка при анализе")

# Helper functions for updating filters
async def update_user_filter_price(user_id: int, price: int, is_min: bool):
    """Update user filter price"""
    db_session = db.SessionLocal()
    try:
        from models import UserFilter
        user_filter = db_session.query(UserFilter).filter(UserFilter.user_id == user_id).first()
        
        if user_filter:
            if is_min:
                user_filter.price_min = price
            else:
                user_filter.price_max = price
        else:
            # Create new filter if doesn't exist
            user_filter = UserFilter(
                user_id=user_id,
                price_min=price if is_min else None,
                price_max=price if not is_min else None
            )
            db_session.add(user_filter)
        
        db_session.commit()
        logger.info(f"Updated price filter for user {user_id}: {'min' if is_min else 'max'} = {price}")
        
    except Exception as e:
        logger.error(f"Error updating price filter: {e}")
        db_session.rollback()
    finally:
        db_session.close()

async def update_user_filter_rooms(user_id: int, rooms: int, is_min: bool):
    """Update user filter rooms"""
    db_session = db.SessionLocal()
    try:
        from models import UserFilter
        user_filter = db_session.query(UserFilter).filter(UserFilter.user_id == user_id).first()
        
        if user_filter:
            if is_min:
                user_filter.rooms_min = rooms
            else:
                user_filter.rooms_max = rooms
        else:
            # Create new filter if doesn't exist
            user_filter = UserFilter(
                user_id=user_id,
                rooms_min=rooms if is_min else None,
                rooms_max=rooms if not is_min else None
            )
            db_session.add(user_filter)
        
        db_session.commit()
        logger.info(f"Updated rooms filter for user {user_id}: {'min' if is_min else 'max'} = {rooms}")
        
    except Exception as e:
        logger.error(f"Error updating rooms filter: {e}")
        db_session.rollback()
    finally:
        db_session.close()

# FSM handlers
@router.message(UserStates.waiting_for_city)
async def handle_city_input(message: types.Message, state: FSMContext):
    """Handle city input"""
    user = await db.get_user(message.from_user.id)
    
    await state.update_data(city=message.text)
    await state.set_state(UserStates.waiting_for_price_min)
    
    await message.answer(get_text("enter_price_min", user.get('language', 'de')), parse_mode=ParseMode.MARKDOWN_V2)

@router.message(UserStates.waiting_for_price_min)
async def handle_price_min_input(message: types.Message, state: FSMContext):
    """Handle minimum price input"""
    user = await db.get_user(message.from_user.id)
    language = user.get('language', 'de')
    text = (message.text or "").strip()
    
    # Handle empty input (skip minimum price)
    if not text:
        await state.update_data(price_min=None)
        await state.set_state(UserStates.waiting_for_price_max)
        await message.answer(
            get_text("enter_price_max", language),
            reply_markup=get_initial_price_selection_keyboard(is_min=False, language=language)
        )
        return
    
    # Support range formats like "300-1500" or "300+"
    if "-" in text:
        parts = [p.strip() for p in text.split("-", 1)]
        try:
            price_min = float(parts[0]) if parts[0] else None
            price_max = float(parts[1]) if parts[1] else None
            if price_min is not None and price_min < 0:
                raise ValueError()
            if price_max is not None and price_max < 0:
                raise ValueError()
        except ValueError:
            await message.answer(
                get_text("invalid_price", language),
                reply_markup=get_initial_price_selection_keyboard(is_min=True, language=language)
            )
            return
        await state.update_data(price_min=price_min, price_max=price_max)
        # Jump directly to rooms min since both bounds are set
        await state.set_state(UserStates.waiting_for_rooms_min)
        await message.answer(
            f"{format_price_range(price_min, price_max, language)}\n\n" + get_text("enter_rooms_min", language),
            reply_markup=get_initial_rooms_selection_keyboard(is_min=True, language=language)
        )
        return
    if text.endswith("+"):
        base = text[:-1].strip()
        try:
            price_min = float(base)
            if price_min < 0:
                raise ValueError()
        except ValueError:
            await message.answer(
                get_text("invalid_price", language),
                reply_markup=get_initial_price_selection_keyboard(is_min=True, language=language)
            )
            return
        await state.update_data(price_min=price_min, price_max=None)
        # Jump to rooms min
        await state.set_state(UserStates.waiting_for_rooms_min)
        await message.answer(
            f"{format_price_range(price_min, None, language)}\n\n" + get_text("enter_rooms_min", language),
            reply_markup=get_initial_rooms_selection_keyboard(is_min=True, language=language)
        )
        return
    
    # Single numeric min
    try:
        price_min = float(text)
        if price_min < 0:
            raise ValueError()
    except ValueError:
        await message.answer(
            get_text("invalid_price", language),
            reply_markup=get_initial_price_selection_keyboard(is_min=True, language=language)
        )
        return
    
    await state.update_data(price_min=price_min)
    await state.set_state(UserStates.waiting_for_price_max)
    
    await message.answer(
        get_text("enter_price_max", language),
        reply_markup=get_initial_price_selection_keyboard(is_min=False, language=language)
    )

@router.message(UserStates.waiting_for_price_max)
async def handle_price_max_input(message: types.Message, state: FSMContext):
    """Handle maximum price input"""
    user = await db.get_user(message.from_user.id)
    
    try:
        price_max = float(message.text)
        if price_max < 0:
            raise ValueError()
    except ValueError:
        await message.answer(
            get_text("invalid_price", user.get('language', 'de')),
            reply_markup=get_initial_price_selection_keyboard(is_min=False, language=user.get('language', 'de'))
        )
        return
    
    await state.update_data(price_max=price_max)
    await state.set_state(UserStates.waiting_for_rooms_min)
    
    await message.answer(
        get_text("enter_rooms_min", user.get('language', 'de')),
        reply_markup=get_initial_rooms_selection_keyboard(is_min=True, language=user.get('language', 'de'))
    )

@router.message(UserStates.waiting_for_rooms_min)
async def handle_rooms_min_input(message: types.Message, state: FSMContext):
    """Handle minimum rooms input"""
    user = await db.get_user(message.from_user.id)
    language = user.get('language', 'de')
    text = (message.text or "").strip()
    
    # Handle empty input (skip minimum rooms)
    if not text:
        await state.update_data(rooms_min=None)
        await state.set_state(UserStates.waiting_for_rooms_max)
        await message.answer(
            get_text("enter_rooms_max", language),
            reply_markup=get_initial_rooms_selection_keyboard(is_min=False, language=language)
        )
        return
    
    # Support range formats like "2-4" or "2+"
    if "-" in text:
        parts = [p.strip() for p in text.split("-", 1)]
        try:
            rooms_min = int(parts[0]) if parts[0] else None
            rooms_max = int(parts[1]) if parts[1] else None
            if rooms_min is not None and rooms_min < 0:
                raise ValueError()
            if rooms_max is not None and rooms_max < 0:
                raise ValueError()
        except ValueError:
            await message.answer(
                get_text("invalid_rooms", language),
                reply_markup=get_initial_rooms_selection_keyboard(is_min=True, language=language)
            )
            return
        await state.update_data(rooms_min=rooms_min, rooms_max=rooms_max)
        # We now have both, proceed to save filters
        filters_data = await state.get_data()
        await db.save_user_filter(user['telegram_id'], filters_data)
        await state.clear()
        # Show summary
        price_min = filters_data.get('price_min')
        price_max = filters_data.get('price_max')
        summary = f"""
{get_text("filters_saved", language)}

{get_text("filters_summary", language)}
{get_text("city_filter", language, city=get_text("city", language), city_name=filters_data.get('city', get_text("any", language)))}
{format_price_range(price_min, price_max, language)}
{format_rooms_range(rooms_min, rooms_max, language)}
{get_text("german_market_tip", language)}
        """
        await message.answer(summary)
        await show_available_apartments(message.from_user.id, filters_data, language)
        return
    if text.endswith("+"):
        base = text[:-1].strip()
        try:
            rooms_min = int(base)
            if rooms_min < 0:
                raise ValueError()
        except ValueError:
            await message.answer(
                get_text("invalid_rooms", language),
                reply_markup=get_initial_rooms_selection_keyboard(is_min=True, language=language)
            )
            return
        await state.update_data(rooms_min=rooms_min, rooms_max=None)
        # Ask for rooms max next
        await state.set_state(UserStates.waiting_for_rooms_max)
        await message.answer(
            get_text("enter_rooms_max", language),
            reply_markup=get_initial_rooms_selection_keyboard(is_min=False, language=language)
        )
        return
    
    # Single numeric min
    try:
        rooms_min = int(text)
        if rooms_min < 0:
            raise ValueError()
    except ValueError:
        await message.answer(
            get_text("invalid_rooms", language),
            reply_markup=get_initial_rooms_selection_keyboard(is_min=True, language=language)
        )
        return
    
    await state.update_data(rooms_min=rooms_min)
    await state.set_state(UserStates.waiting_for_rooms_max)
    
    await message.answer(
        get_text("enter_rooms_max", language),
        reply_markup=get_initial_rooms_selection_keyboard(is_min=False, language=user.get('language', 'de'))
    )

@router.message(UserStates.waiting_for_rooms_max)
async def handle_rooms_max_input(message: types.Message, state: FSMContext):
    """Handle maximum rooms input"""
    user = await db.get_user(message.from_user.id)
    
    try:
        rooms_max = int(message.text)
        if rooms_max < 0:
            raise ValueError()
    except ValueError:
        await message.answer(
            get_text("invalid_rooms", user.get('language', 'de')),
            reply_markup=get_initial_rooms_selection_keyboard(is_min=False, language=user.get('language', 'de'))
        )
        return
    
    await state.update_data(rooms_max=rooms_max)
    
    # Save filters to database immediately after basic setup
    filters_data = await state.get_data()
    
    # Save or update user filters in MongoDB
    await db.save_user_filter(user['telegram_id'], filters_data)
    
    # Debug: Log saved filter
    logger.info(f"Saved filter for user {user['telegram_id']}: city={filters_data.get('city')}, price={filters_data.get('price_min')}-{filters_data.get('price_max')}, rooms={filters_data.get('rooms_min')}-{filters_data.get('rooms_max')}")
    
    await state.clear()
    
    # Create success message with filter summary
    # Format values properly - handle None values correctly
    language = user.get('language', 'de')
    price_min = filters_data.get('price_min')
    price_max = filters_data.get('price_max')
    rooms_min = filters_data.get('rooms_min')
    rooms_max = filters_data.get('rooms_max')
    
    filter_summary = f"""
{get_text("filters_saved", language)}

{get_text("filters_summary", language)}
{get_text("city_filter", language, city=get_text("city", language), city_name=filters_data.get('city', get_text("any", language)))}
{format_price_range(price_min, price_max, language)}
{format_rooms_range(rooms_min, rooms_max, language)}

{get_text("german_market_tip", language)}
    """
    
    await message.answer(
        filter_summary,
        reply_markup=get_main_menu_keyboard(user.get('language', 'de'))
    )
    
    # Show available apartments immediately
    await show_available_apartments(message.from_user.id, filters_data, user.get('language', 'de'))

# Settings FSM handlers for manual input
@router.message(UserStates.waiting_for_settings_price_min)
async def handle_settings_price_min_input(message: types.Message, state: FSMContext):
    """Handle manual minimum price input in settings"""
    text = (message.text or "").strip()
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    if "-" in text:
        parts = [p.strip() for p in text.split("-", 1)]
        try:
            price_min = int(parts[0]) if parts[0] else None
            price_max = int(parts[1]) if parts[1] else None
            if (price_min is not None and price_min < 0) or (price_max is not None and price_max < 0):
                raise ValueError()
        except ValueError:
            await message.answer("❌ Неверная цена. Используйте формат 300, 300-1500 или 300+.")
            return
    elif text.endswith("+"):
        base = text[:-1].strip()
        try:
            price_min = int(base)
            if price_min < 0:
                raise ValueError()
        except ValueError:
            await message.answer("❌ Неверная цена. Используйте формат 300, 300-1500 или 300+.")
            return
    else:
        try:
            price_min = int(text)
            if price_min < 0:
                raise ValueError()
        except ValueError:
            await message.answer("❌ Неверная цена. Введите положительное число.")
            return
    
    user = await db.get_user(message.from_user.id)
    # Update filter in MongoDB, preserve other bound if present
    user_filter = await db.get_user_filter(user['telegram_id'])
    update_payload: dict = {}
    if price_min is not None:
        update_payload["price_min"] = price_min
    if price_max is not None:
        update_payload["price_max"] = price_max
    if user_filter:
        await db.user_filters_collection.update_one(
            {"user_id": user['telegram_id']},
            {"$set": update_payload}
        )
    else:
        await db.save_user_filter(user['telegram_id'], update_payload)
    
    await state.clear()
    # Determine current values to show
    current_min = update_payload.get("price_min")
    current_max = update_payload.get("price_max") if price_max is not None else (user_filter.get("price_max") if user_filter else None)
    language = user.get('language', 'de')
    await message.answer(
        format_price_range(current_min, current_max, language),
        reply_markup=get_price_selection_keyboard(current_price=current_min, is_min=True, language=language)
    )

@router.message(UserStates.waiting_for_settings_price_max)
async def handle_settings_price_max_input(message: types.Message, state: FSMContext):
    """Handle manual maximum price input in settings"""
    try:
        price = int(message.text)
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Неверная цена. Введите положительное число.")
        return
    
    user = await db.get_user(message.from_user.id)
    # Update filter in MongoDB
    user_filter = await db.get_user_filter(user['telegram_id'])
    if user_filter:
        await db.user_filters_collection.update_one(
            {"user_id": user['telegram_id']},
            {"$set": {"price_max": price}}
        )
    else:
        await db.save_user_filter(user['telegram_id'], {"price_max": price})
    
    await state.clear()
    await message.answer(
        f"💰 Максимальная цена\n\nТекущее значение: {price}€",
        reply_markup=get_price_selection_keyboard(current_price=price, is_min=False, language=user.get('language', 'de'))
    )

@router.message(UserStates.waiting_for_settings_rooms_min)
async def handle_settings_rooms_min_input(message: types.Message, state: FSMContext):
    """Handle manual minimum rooms input in settings"""
    text = (message.text or "").strip()
    rooms_min: Optional[int] = None
    rooms_max: Optional[int] = None
    if "-" in text:
        parts = [p.strip() for p in text.split("-", 1)]
        try:
            rooms_min = int(parts[0]) if parts[0] else None
            rooms_max = int(parts[1]) if parts[1] else None
            if (rooms_min is not None and rooms_min < 0) or (rooms_max is not None and rooms_max < 0):
                raise ValueError()
        except ValueError:
            await message.answer("❌ Неверное количество комнат. Используйте формат 2, 2-4 или 2+.")
            return
    elif text.endswith("+"):
        base = text[:-1].strip()
        try:
            rooms_min = int(base)
            if rooms_min < 0:
                raise ValueError()
        except ValueError:
            await message.answer("❌ Неверное количество комнат. Используйте формат 2, 2-4 или 2+.")
            return
    else:
        try:
            rooms_min = int(text)
            if rooms_min < 0:
                raise ValueError()
        except ValueError:
            await message.answer("❌ Неверное количество комнат. Введите положительное число.")
            return
    
    user = await db.get_user(message.from_user.id)
    # Update filter in MongoDB
    user_filter = await db.get_user_filter(user['telegram_id'])
    update_payload: dict = {}
    if rooms_min is not None:
        update_payload["rooms_min"] = rooms_min
    if rooms_max is not None:
        update_payload["rooms_max"] = rooms_max
    if user_filter:
        await db.user_filters_collection.update_one(
            {"user_id": user['telegram_id']},
            {"$set": update_payload}
        )
    else:
        await db.save_user_filter(user['telegram_id'], update_payload)
    
    await state.clear()
    language = user.get('language', 'de')
    current_min = update_payload.get("rooms_min")
    current_max = update_payload.get("rooms_max") if rooms_max is not None else (user_filter.get("rooms_max") if user_filter else None)
    await message.answer(
        format_rooms_range(current_min, current_max, language),
        reply_markup=get_rooms_selection_keyboard(current_rooms=current_min, is_min=True, language=language)
    )

@router.message(UserStates.waiting_for_settings_rooms_max)
async def handle_settings_rooms_max_input(message: types.Message, state: FSMContext):
    """Handle manual maximum rooms input in settings"""
    try:
        rooms = int(message.text)
        if rooms < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Неверное количество комнат. Введите положительное число.")
        return
    
    user = await db.get_user(message.from_user.id)
    # Update filter in MongoDB
    user_filter = await db.get_user_filter(user['telegram_id'])
    if user_filter:
        await db.user_filters_collection.update_one(
            {"user_id": user['telegram_id']},
            {"$set": {"rooms_max": rooms}}
        )
    else:
        await db.save_user_filter(user['telegram_id'], {"rooms_max": rooms})
    
    await state.clear()
    room_text = f"{rooms} {'комната' if rooms == 1 else 'комнаты' if rooms < 5 else 'комнат'}"
    await message.answer(
        f"🏠 Максимум комнат\n\nТекущее значение: {room_text}",
        reply_markup=get_rooms_selection_keyboard(current_rooms=rooms, is_min=False, language=user.get('language', 'de'))
    )

# Admin commands
@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Admin commands"""
    if message.from_user.id not in [5988666438]:  # Add admin user IDs
        return
    
    admin_text = """
🔧 Админ команды:
/start_monitoring - Запустить мониторинг квартир
/stop_monitoring - Остановить мониторинг квартир
/status - Получить статус мониторинга
/force_check - Принудительная проверка квартир
/reset_subscription - Сбросить подписку пользователя (для тестирования)
/clean_bad_urls - Очистить квартиры с плохими URL
    """
    
    await message.answer(admin_text, parse_mode=ParseMode.MARKDOWN_V2)

@router.message(Command("reset_subscription"))
async def cmd_reset_subscription(message: types.Message):
    """Reset user subscription for testing"""
    # Remove admin check for testing
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("Пользователь не найден")
        return
    
    # Delete active subscription from MongoDB
    result = await db.subscriptions_collection.delete_one({
        "user_id": user['telegram_id'],
        "is_active": True
    })
    
    if result.deleted_count > 0:
        await message.answer("✅ Подписка сброшена! Используйте /start для отображения кнопки оплаты.")
    else:
        await message.answer("Активная подписка не найдена.")

@router.message(Command("start_monitoring"))
async def cmd_start_monitoring(message: types.Message):
    """Start monitoring"""
    if message.from_user.id not in [123456789]:
        return
    
    try:
        from monitor import start_monitoring_service
        await start_monitoring_service()
        await message.answer("✅ Мониторинг запущен")
        
        # Also clean bad URLs when starting monitoring
        try:
            bad_urls_filter = {
                "application_url": {"$regex": "Suche/de/.*wohnung-mieten"}
            }
            
            bad_count = await db.apartments_collection.count_documents(bad_urls_filter)
            if bad_count > 0:
                result = await db.apartments_collection.delete_many(bad_urls_filter)
                await message.answer(f"✅ Автоматически удалено {result.deleted_count} квартир с неправильными URL")
            
            # Also clean apartments with URLs that don't contain 'expose'
            non_expose_filter = {
                "application_url": {"$not": {"$regex": "expose"}}
            }
            
            non_expose_count = await db.apartments_collection.count_documents(non_expose_filter)
            if non_expose_count > 0:
                result2 = await db.apartments_collection.delete_many(non_expose_filter)
                await message.answer(f"✅ Также удалено {result2.deleted_count} квартир с URL без 'expose'")
                
        except Exception as e:
            logger.error(f"Error auto-cleaning bad URLs: {e}")
            
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        await message.answer(f"❌ Ошибка при запуске мониторинга: {e}")

@router.message(Command("stop_monitoring"))
async def cmd_stop_monitoring(message: types.Message):
    """Stop monitoring"""
    if message.from_user.id not in [123456789]:
        return
    
    try:
        from monitor import stop_monitoring_service
        await stop_monitoring_service()
        await message.answer("⏹️ Мониторинг остановлен")
        
        # Also clean bad URLs when stopping monitoring
        try:
            bad_urls_filter = {
                "application_url": {"$regex": "Suche/de/.*wohnung-mieten"}
            }
            
            bad_count = await db.apartments_collection.count_documents(bad_urls_filter)
            if bad_count > 0:
                result = await db.apartments_collection.delete_many(bad_urls_filter)
                await message.answer(f"✅ Автоматически удалено {result.deleted_count} квартир с неправильными URL")
        except Exception as e:
            logger.error(f"Error auto-cleaning bad URLs: {e}")
            
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        await message.answer(f"❌ Ошибка при остановке мониторинга: {e}")

@router.message(Command("status"))
async def cmd_status(message: types.Message):
    """Get monitoring status"""
    if message.from_user.id not in [123456789]:
        return
    
    try:
        from monitor import get_monitoring_status
        status = await get_monitoring_status()
        
        # Also count apartments with bad URLs
        bad_urls_filter = {
            "application_url": {"$regex": "Suche/de/.*wohnung-mieten"}
        }
        bad_count = await db.apartments_collection.count_documents(bad_urls_filter)
        
        status_text = f"""
📊 Статус мониторинга:
Запущен: {status['is_running']}
Известных квартир: {status['known_apartments_count']}
Последняя проверка: {status['last_check']}
Квартир с плохими URL: {bad_count}
        """
        
        await message.answer(status_text)
        
        if bad_count > 0:
            await message.answer(f"⚠️ Обнаружено {bad_count} квартир с неправильными URL. Используйте /clean_bad_urls для очистки.")
            
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        await message.answer(f"❌ Ошибка при получении статуса: {e}")

@router.message(Command("clean_bad_urls"))
async def cmd_clean_bad_urls(message: types.Message):
    """Clean ALL apartments and start fresh with only neubau"""
    # Remove admin check for testing
    # if message.from_user.id not in [123456789]:
    #     return
    
    try:
        # Count total apartments before cleanup
        total_count = await db.apartments_collection.count_documents({})
        await message.answer(f"🗑️ Удаляю ВСЕ {total_count} квартир из базы...")
        
        # Delete ALL apartments to start fresh
        result = await db.apartments_collection.delete_many({})
        
        await message.answer(f"✅ Удалено {result.deleted_count} квартир. База очищена!")
        await message.answer("🔄 Теперь запустите /force_check для поиска только neubau квартир")
        
    except Exception as e:
        logger.error(f"Error cleaning all apartments: {e}")
        await message.answer(f"❌ Ошибка при очистке: {e}")

@router.message(Command("force_check"))
async def cmd_force_check(message: types.Message):
    """Force apartment check"""
    # Remove admin check for testing
    # if message.from_user.id not in [123456789]:
    #     return
    
    try:
        from monitor import force_apartment_check
        await force_apartment_check()
        await message.answer("✅ Принудительная проверка квартир запущена")
    except Exception as e:
        logger.error(f"Error in force check: {e}")
        await message.answer(f"❌ Ошибка при принудительной проверке: {e}")
        
    # Also clean bad URLs after force check
    try:
        bad_urls_filter = {
            "application_url": {"$regex": "Suche/de/.*wohnung-mieten"}
        }
        
        bad_count = await db.apartments_collection.count_documents(bad_urls_filter)
        if bad_count > 0:
            result = await db.apartments_collection.delete_many(bad_urls_filter)
            await message.answer(f"✅ Автоматически удалено {result.deleted_count} квартир с неправильными URL")
        
        # Also clean apartments with URLs that don't contain 'expose'
        non_expose_filter = {
            "application_url": {"$not": {"$regex": "expose"}}
        }
        
        non_expose_count = await db.apartments_collection.count_documents(non_expose_filter)
        if non_expose_count > 0:
            result2 = await db.apartments_collection.delete_many(non_expose_filter)
            await message.answer(f"✅ Также удалено {result2.deleted_count} квартир с URL без 'expose'")
            
    except Exception as e:
        logger.error(f"Error auto-cleaning bad URLs: {e}")

async def show_available_apartments(user_id: int, filters_data: dict, language: str = "de"):
    """Show available apartments to user based on their filters"""
    try:
        # Debug: Log filters
        logger.info(f"Searching apartments with filters: {filters_data}")
        logger.info(f"City filter: '{filters_data.get('city', 'None')}'")
        logger.info(f"Price range: {filters_data.get('price_min', 'None')} - {filters_data.get('price_max', 'None')}")
        logger.info(f"Rooms range: {filters_data.get('rooms_min', 'None')} - {filters_data.get('rooms_max', 'None')}")
        
        # Get apartments from MongoDB first (limit to 10), then filter out zero-only
        apartments = await db.get_apartments_by_filters(filters_data, limit=10)
        def non_empty_apartment(a: dict) -> bool:
            try:
                if not isinstance(a, dict):
                    return False
                price = a.get('price') or 0
                rooms = a.get('rooms') or 0
                area = a.get('area') or 0
                title = str(a.get('title', '')).strip()
                desc = str(a.get('description', '')).strip()
                url = str(a.get('original_url') or a.get('application_url') or '').strip()
                return (price > 0 or rooms > 0 or area > 0 or len(title) > 10 or len(desc) > 20 or bool(url))
            except Exception:
                return True
        apartments = [a for a in apartments if non_empty_apartment(a)]
        
        # Debug: Log results
        logger.info(f"Found {len(apartments)} apartments in database")
        for apt in apartments:
            logger.info(f"Apartment: {apt.get('title', 'No title')} - {apt.get('city', 'No city')} - {apt.get('price', 0)}€ - {apt.get('rooms', 0)} rooms")
        
        # Always try to supplement with live fetch to reach up to 6 total (1 из БД + 5 live), стараемся разнообразить источники
        needed_from_db = 1
        db_pick = apartments[:needed_from_db]
        live_pick: list = []
        if len(db_pick) < 6:
            # Live fetch via unified real API (Apify-backed) to avoid ожидания мониторинга
            try:
                from scrapers import ScraperManager
                async with ScraperManager() as sm:
                    fresh = await sm.search_all_sites(filters_data)

                # Отфильтруем под текущие фильтры пользователя, если возможно
                def match_filters(a: dict) -> bool:
                    try:
                        if not isinstance(a, dict):
                            return False
                        if filters_data.get('city') and a.get('city'):
                            if filters_data['city'].lower() not in str(a.get('city', '')).lower():
                                return False
                        price = a.get('price') or 0
                        if filters_data.get('price_min') is not None and price < filters_data['price_min']:
                            return False
                        if filters_data.get('price_max') is not None and price > filters_data['price_max']:
                            return False
                        rooms = a.get('rooms') or 0
                        if filters_data.get('rooms_min') is not None and rooms < filters_data['rooms_min']:
                            return False
                        if filters_data.get('rooms_max') is not None and rooms > filters_data['rooms_max']:
                            return False
                        return True
                    except Exception:
                        return True

                filtered_fresh = [a for a in fresh if isinstance(a, dict) and match_filters(a)]

                # Если после фильтрации пусто — всё равно возьмем первые свежие
                send_now = filtered_fresh if filtered_fresh else [a for a in fresh if isinstance(a, dict)]

                # Уберем дубликаты по (source, external_id)
                def key_of(a: dict):
                    return (a.get('source'), a.get('external_id'))
                existing_keys = {key_of(a) for a in db_pick if isinstance(a, dict)}
                uniq = []
                for a in send_now:
                    if key_of(a) in existing_keys:
                        continue
                    uniq.append(a)
                    existing_keys.add(key_of(a))

                # Диверсифицируем источники среди live (IS24, Immowelt и др.)
                by_source = {}
                for a in uniq:
                    src = str(a.get('source') or 'unknown')
                    by_source.setdefault(src, []).append(a)
                # Round-robin от источников
                rr = []
                while len(rr) < 3 and any(by_source.values()):
                    for src in list(by_source.keys()):
                        lst = by_source.get(src) or []
                        if lst:
                            rr.append(lst.pop(0))
                            if len(rr) == 3:
                                break
                        else:
                            by_source.pop(src, None)
                live_pick = rr

                # Параллельно сохраним их в БД (не блокирует отправку)
                saved = 0
                for apt in live_pick:
                    try:
                        apt_id = await db.save_apartment(apt)
                        if apt_id:
                            saved += 1
                    except Exception:
                        continue

                logger.info(f"Live fetch fetched {len(fresh)}, filtered {len(filtered_fresh)}, saved {saved}, taking live {len(live_pick)}")
            except Exception as e:
                logger.error(f"Live fetch fallback failed: {e}")
                live_pick = []
            # Если после всех действий пусто — сообщим и выйдем
            if not db_pick and not live_pick:
                await bot.send_message(
                    user_id,
                    "🔍 По вашим фильтрам пока нет доступных квартир.\n\n"
                    "Бот будет мониторить новые предложения и уведомит вас, когда появятся подходящие варианты!"
                )
                return

        # Объединяем: сначала 3 из БД, затем до 3 live
        apartments_to_show = [a for a in db_pick if isinstance(a, dict)] + [a for a in live_pick if isinstance(a, dict)]
        # How many we actually show now
        total_available = len(apartments_to_show)
        if not apartments_to_show:
            await bot.send_message(user_id, "📭 Подходящих объявлений пока нет.")
            return

        # Сообщение о количестве (сколько покажем прямо сейчас)
        await bot.send_message(user_id, f"🏠 Найдено {total_available} квартир по вашим фильтрам:")
        
        # Send each apartment (up to 6 total in this batch) using the same notifier formatting
        from notifications import send_apartment_notification
        for apartment in apartments_to_show[:6]:
            await send_apartment_notification(user_id, apartment, language)
            await asyncio.sleep(0.5)
        
        # Send summary with "Show more" if можем показать больше
        # Показываем кнопки если найдено больше 3 квартир (чтобы всегда показывать кнопки)
        total_apartments = len([a for a in apartments if isinstance(a, dict)])
        if total_apartments > 3:
            keyboard = InlineKeyboardBuilder()
            keyboard.add(InlineKeyboardButton(
                text="📋 Показать ещё",
                callback_data="show_more_apartments"
            ))
            keyboard.add(InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data="refresh_apartments"
            ))
            keyboard.adjust(2)
            
            await bot.send_message(
                user_id,
                f"💡 Показаны первые {len(apartments_to_show)} из {total_apartments} квартир. Бот будет уведомлять вас о новых предложениях!",
                reply_markup=keyboard.as_markup()
            )
        else:
            await bot.send_message(
                user_id,
                "💡 Бот будет уведомлять вас о новых предложениях!"
            )
        
    except Exception as e:
        logger.error(f"Error showing apartments to user {user_id}: {e}")
        await bot.send_message(
            user_id,
            "❌ Ошибка при загрузке квартир. Попробуйте позже."
        )

# Handler for "Show more apartments" button
@router.callback_query(TextFilter(text="show_more_apartments"))
async def handle_show_more_apartments(callback: types.CallbackQuery):
    """Handle show more apartments button"""
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    filters_data = {
        'city': user.get('city'),
        'price_min': user.get('price_min'),
        'price_max': user.get('price_max'),
        'rooms_min': user.get('rooms_min'),
        'rooms_max': user.get('rooms_max'),
        'keywords': user.get('keywords', [])
    }
    
    # Get more apartments (skip first 5) + подмешиваем live и разнообразим источники
    try:
        db_more = await db.get_apartments_by_filters(filters_data, limit=10, skip=5)
        db_more = [a for a in db_more if isinstance(a, dict)]
        
        # Live свежие
        live_more: list = []
        try:
            from scrapers import ScraperManager
            async with ScraperManager() as sm:
                fresh = await sm.search_all_sites(filters_data)
            def match_filters(a: dict) -> bool:
                try:
                    if filters_data.get('city') and a.get('city'):
                        if filters_data['city'].lower() not in str(a.get('city','')).lower():
                            return False
                    price = a.get('price') or 0
                    if filters_data.get('price_min') is not None and price < filters_data['price_min']:
                        return False
                    if filters_data.get('price_max') is not None and price > filters_data['price_max']:
                        return False
                    rooms = a.get('rooms') or 0
                    if filters_data.get('rooms_min') is not None and rooms < filters_data['rooms_min']:
                        return False
                    if filters_data.get('rooms_max') is not None and rooms > filters_data['rooms_max']:
                        return False
                    return True
                except Exception:
                    return True
            filtered_fresh = [a for a in fresh if isinstance(a, dict) and match_filters(a)]
            # Удалим дубль из БД по (source, external_id)
            def key_of(a: dict):
                return (a.get('source'), a.get('external_id'))
            existing_keys = {key_of(a) for a in db_more}
            uniq = []
            for a in filtered_fresh:
                if key_of(a) in existing_keys:
                    continue
                uniq.append(a)
                existing_keys.add(key_of(a))
            # Диверсифицируем источники и возьмём до 5 всего
            by_source = {}
            for a in uniq:
                src = str(a.get('source') or 'unknown')
                by_source.setdefault(src, []).append(a)
            rr_live = []
            while len(rr_live) < 5 and any(by_source.values()):
                for src in list(by_source.keys()):
                    lst = by_source.get(src) or []
                    if lst:
                        rr_live.append(lst.pop(0))
                        if len(rr_live) == 5:
                            break
                    else:
                        by_source.pop(src, None)
            live_more = rr_live
        except Exception as e:
            logger.error(f"Show more live fetch failed: {e}")
            live_more = []

        # Скомбинируем: до 3 из БД и до 2 live, итого до 5
        take_db = db_more[:3]
        # round-robin разных источников при объединении
        combined: list = []
        sources_buckets = {
            'db': take_db,
            'live': live_more
        }
        order = ['db','live']
        while len(combined) < 5 and any(sources_buckets[k] for k in order):
            for k in order:
                bucket = sources_buckets[k]
                if bucket:
                    combined.append(bucket.pop(0))
                    if len(combined) == 5:
                        break

        if not combined:
            await callback.answer("📭 Больше квартир не найдено")
            return

        # Отправим через единый форматер с фото/описанием
        from notifications import send_apartment_notification
        for apartment in combined:
            await send_apartment_notification(callback.from_user.id, apartment, user.get('language','de'))
            await asyncio.sleep(0.5)
        
        # Check if there are more DB apartments (для кнопок ориентируемся на БД)
        remaining = len(db_more) - 5
        if remaining > 0 or len(apartments_to_show) > 3:
            keyboard = InlineKeyboardBuilder()
            keyboard.add(InlineKeyboardButton(
                text="📋 Показать ещё",
                callback_data="show_more_apartments"
            ))
            keyboard.add(InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data="refresh_apartments"
            ))
            keyboard.adjust(2)
            
            await bot.send_message(
                callback.from_user.id,
                f"💡 Показано ещё 5 квартир. Осталось: {remaining}",
                reply_markup=keyboard.as_markup()
            )
        else:
            await bot.send_message(
                callback.from_user.id,
                "✅ Все доступные квартир показаны!"
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing more apartments: {e}")
        await callback.answer("❌ Ошибка при загрузке квартир")

# Handler for "Refresh apartments" button
@router.callback_query(TextFilter(text="refresh_apartments"))
async def handle_refresh_apartments(callback: types.CallbackQuery):
    """Handle refresh apartments button"""
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    filters_data = {
        'city': user.get('city'),
        'price_min': user.get('price_min'),
        'price_max': user.get('price_max'),
        'rooms_min': user.get('rooms_min'),
        'rooms_max': user.get('rooms_max'),
        'keywords': user.get('keywords', [])
    }
    
    await callback.answer("🔄 Обновляем список квартир...")
    await show_available_apartments(callback.from_user.id, filters_data, user.get('language', 'de'))

# Main function
async def main():
    """Main function"""
    logger.info("Starting bot...")
    
    # Connect to MongoDB
    if not await db.connect():
        logger.error("Failed to connect to MongoDB. Exiting.")
        return
    
    # Set bot instance for notifications
    set_bot_instance(bot)
    
    # Set bot commands
    await set_bot_commands()
    
    # Start monitoring service
    await start_monitoring_service()
    
    # Start cache cleanup task
    cache_cleanup_task = asyncio.create_task(cleanup_caches())
    
    # Start bot
    try:
        await dp.start_polling(bot)
    finally:
        cache_cleanup_task.cancel()
        await stop_monitoring_service()
        await db.disconnect()
        await bot.session.close()

async def set_bot_commands():
    """Set bot commands for the command menu"""
    commands = [
        types.BotCommand(command="start", description="🏠 Запустить бота / Start bot / Запустити бота"),
        types.BotCommand(command="language", description="🌍 Сменить язык / Change language / Змінити мову"),
        types.BotCommand(command="help", description="❓ Помощь / Help / Допомога"),
        types.BotCommand(command="settings", description="⚙️ Настройки / Settings / Налаштування"),
        types.BotCommand(command="filters", description="🔍 Фильтры поиска / Search filters / Фільтри пошуку"),
        types.BotCommand(command="subscription", description="💳 Подписка / Subscription / Підписка"),
        types.BotCommand(command="stats", description="📊 Статистика / Statistics / Статистика"),
    ]
    
    try:
        await bot.set_my_commands(commands)
        logger.info("Bot commands set successfully")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

if __name__ == "__main__":
    asyncio.run(main())
