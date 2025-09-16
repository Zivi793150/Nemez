import logging
from aiogram import Bot
import aiohttp
import re
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode
from config import Config
from locales import get_text
from ai_analyzer import analyze_apartment_ai

logger = logging.getLogger(__name__)

# Глобальная переменная для бота (будет установлена позже)
bot_instance = None

def set_bot_instance(bot: Bot):
    """Установить экземпляр бота для отправки уведомлений"""
    global bot_instance
    bot_instance = bot

def get_apartment_keyboard(apartment, language="de"):
    """Get apartment notification keyboard"""
    builder = InlineKeyboardBuilder()
    
    # Add apply button: prefer explicit application_url, fallback to original_url
    application_url = str(apartment.get('application_url') or apartment.get('original_url') or '').strip()
    if application_url and application_url.startswith('http'):
        builder.add(InlineKeyboardButton(
            text=get_text("apply_now", language) if get_text("apply_now", language) else "📝 Подать заявку", 
            url=application_url
        ))
    
    # Optional: favorite / hide via callbacks (обработчики можно добавить позже безопасно)
    apt_id = str(apartment.get('_id', apartment.get('external_id', '0')))
    builder.add(InlineKeyboardButton(
        text=get_text("save_favorite", language) or "⭐ В избранное",
        callback_data=f"fav_{apt_id}"
    ))
    builder.add(InlineKeyboardButton(
        text=get_text("hide_item", language) or "🙈 Скрыть",
        callback_data=f"hide_{apt_id}"
    ))
    
    if Config.ENABLE_AI_ANALYSIS:
        builder.add(InlineKeyboardButton(
            text=get_text("ai_analyze", language) or "🤖 AI Анализ", 
            callback_data=f"ai_analysis_{apt_id}"
        ))
    
    builder.adjust(1)
    return builder.as_markup()

async def send_apartment_notification(user_id: int, apartment, language: str = "de"):
    """Send apartment notification to user"""
    if not bot_instance:
        logger.error("Bot instance not set")
        return
        
    try:
        # Try to collect images
        images = []
        raw_images = apartment.get('images')
        if isinstance(raw_images, str):
            try:
                import json
                images = json.loads(raw_images)
            except Exception:
                images = []
        elif isinstance(raw_images, list):
            images = raw_images
        images = [url for url in images if isinstance(url, str) and url.startswith('http')][:10]

        # Full description
        full_description = apartment.get('description', '') or ''

        # Enrich from original listing page if missing
        if (not images or len(images) == 0 or not full_description) and (apartment.get('original_url') or apartment.get('application_url')):
            url = (apartment.get('original_url') or apartment.get('application_url') or '').strip()
            if url.startswith('http'):
                try:
                    timeout = aiohttp.ClientTimeout(total=12)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(url, ssl=False, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                            if resp.status == 200:
                                html = await resp.text()
                                # Build helpers for URL normalization (protocol-relative and relative)
                                base_match = re.match(r'^(https?:)//([^/]+)', url)
                                scheme = base_match.group(1) if base_match else 'https:'
                                host = base_match.group(2) if base_match else ''
                                def normalize(u: str) -> str:
                                    try:
                                        u = u.strip()
                                        if u.startswith('//'):
                                            return f"{scheme}{u}"
                                        if u.startswith('/') and host:
                                            return f"{scheme}//{host}{u}"
                                        return u
                                    except Exception:
                                        return u
                                # og:image variants
                                for pat in [
                                    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
                                    r'<meta[^>]+property=["\']og:image:secure_url["\'][^>]+content=["\']([^"\']+)',
                                    r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)'
                                ]:
                                    for oi in re.findall(pat, html, re.IGNORECASE):
                                        oi = normalize(oi)
                                        if isinstance(oi, str) and oi.startswith('http'):
                                            images.append(oi)
                                # Inline images: src and data-src
                                for src in re.findall(r'<img[^>]+(?:data-src|src)=["\']([^"\']+)["\']', html, re.IGNORECASE):
                                    src = normalize(src)
                                    if isinstance(src, str) and src.startswith('http'):
                                        images.append(src)
                                # Try JSON-LD description first
                                if not full_description:
                                    json_ld_blocks = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>', html, re.IGNORECASE)
                                    for block in json_ld_blocks:
                                        try:
                                            import json
                                            data = json.loads(block.strip())
                                            def pick_desc(obj):
                                                try:
                                                    if isinstance(obj, dict):
                                                        if isinstance(obj.get('description'), str) and obj['description'].strip():
                                                            return obj['description']
                                                        for v in obj.values():
                                                            r = pick_desc(v)
                                                            if r:
                                                                return r
                                                    if isinstance(obj, list):
                                                        for v in obj:
                                                            r = pick_desc(v)
                                                            if r:
                                                                return r
                                                except Exception:
                                                    return None
                                                return None
                                            d = pick_desc(data)
                                            if isinstance(d, str) and d.strip():
                                                full_description = d
                                                break
                                        except Exception:
                                            continue
                                # Fallback: meta descriptions
                                if not full_description:
                                    m = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
                                    if not m:
                                        m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
                                    if m:
                                        full_description = m.group(1)
                except Exception:
                    pass
        preview = (full_description[:900] + '...') if len(full_description) > 900 else full_description

        # Prepare caption with richer details
        price = apartment.get('price', 0)
        rooms = apartment.get('rooms', 0)
        area = apartment.get('area', 0)
        district = apartment.get('district') or ''
        city = (apartment.get('city') or district or '').strip()
        price_m2 = None
        try:
            if price and area and area > 0:
                price_m2 = round(float(price) / float(area))
        except Exception:
            price_m2 = None

        # Translated labels
        lbl_price = get_text("price", language) or "Цена"
        lbl_rooms = get_text("rooms", language) or "Комнаты"
        lbl_area = get_text("area", language) or "Площадь"
        lbl_district = get_text("district", language) or "Район/Город"
        lbl_per_m2 = get_text("per_m2", language) or "за м²"
        src = apartment.get('source') or ''
        source_emoji = "🏡" if src == 'immowelt' else ("🏢" if src == 'immobilienscout24' else "🏠")

        header = f"{source_emoji} {get_text('apartment_in', language) or 'Квартира в'} {city}" if city else f"{source_emoji} {apartment.get('title', 'Без названия')}"

        price_text = f"{int(price)}€" if price and price > 0 else (get_text("no_price", language) or "Цена не указана")
        rooms_text = f"{int(rooms)}" if rooms and rooms > 0 else (get_text("no_value", language) or "Не указано")
        area_text = f"{int(area)}m²" if area and area > 0 else (get_text("no_value", language) or "Не указана")
        district_text = district or city or '—'

        # Tags (best-effort)
        tags = []
        try:
            features = apartment.get('features')
            if isinstance(features, str):
                import json
                features = json.loads(features)
            if isinstance(features, list):
                for f in features[:6]:
                    if isinstance(f, str) and len(f) <= 25:
                        tags.append(f"#{f}")
        except Exception:
            pass
        tags_text = (" ".join(tags)) if tags else ""

        caption_lines = [
            header,
            "",
            f"💰 {lbl_price}: {price_text}" + (f"  •  {price_m2}€ {lbl_per_m2}" if price_m2 else ""),
            f"🛏️ {lbl_rooms}: {rooms_text}",
            f"📐 {lbl_area}: {area_text}",
            f"📍 {lbl_district}: {district_text}",
        ]
        if tags_text:
            caption_lines.append(tags_text)
        caption_lines.extend(["", preview])
        caption = "\n".join(caption_lines)
        # Sanitize escaped markdown artifacts from locales (e.g., \!, \-)
        try:
            caption = caption.replace("\\!", "!").replace("\\-", "-").replace("\\_", "_").replace("\\.", ".")
        except Exception:
            pass
        
        # Always send a single main photo + text (без MediaGroup из-за падений)
        if images:
            try:
                await bot_instance.send_photo(
                    user_id,
                    photo=images[0],
                    caption=caption,
                    reply_markup=get_apartment_keyboard(apartment, language)
                )
            except Exception as e:
                logger.warning(f"Failed to send photo, fallback to text: {e}")
                await bot_instance.send_message(
                    user_id,
                    caption,
                    reply_markup=get_apartment_keyboard(apartment, language)
                )
        else:
            await bot_instance.send_message(
                user_id,
                caption,
                reply_markup=get_apartment_keyboard(apartment, language)
            )
        
    except Exception as e:
        logger.error(f"Error sending apartment notification to {user_id}: {e}")

async def send_ai_analysis(user_id: int, apartment, language: str = "de"):
    """Send AI analysis of apartment to user"""
    if not bot_instance:
        logger.error("Bot instance not set")
        return
        
    try:
        # Convert apartment dict for AI analysis
        apartment_data = {
            'title': apartment.get('title', 'Без названия'),
            'description': apartment.get('description', 'Описание недоступно'),
            'price': apartment.get('price', 0),
            'rooms': apartment.get('rooms', 0),
            'area': apartment.get('area', 0),
            'city': apartment.get('city', 'Не указан'),
            'district': apartment.get('district', 'Не указан'),
            'features': apartment.get('features', [])
        }
        
        # Get AI analysis
        analysis = await analyze_apartment_ai(apartment_data, language)
        
        # Format analysis text
        analysis_text = f"""
🤖 *AI Анализ квартиры*

🏠 *{apartment.get('title', 'Без названия')}*

📊 *Общий балл:* {analysis['overall_score']}/100

✅ *Плюсы:*
"""
        
        for pro in analysis['pros']:
            analysis_text += f"• {pro}\n"
        
        analysis_text += "\n❌ *Минусы:*\n"
        for con in analysis['cons']:
            analysis_text += f"• {con}\n"
        
        analysis_text += "\n💡 *Рекомендации:*\n"
        for rec in analysis['recommendations']:
            analysis_text += f"• {rec}\n"
        
        analysis_text += f"""

📈 *Анализ рынка:*
💰 Цена: {analysis['market_analysis']['price'].get('reason', 'Нет данных')}
📍 Локация: {analysis['market_analysis']['location'].get('reason', 'Нет данных')}
✨ Особенности: {analysis['market_analysis']['features'].get('total_features', 0)} характеристик
"""

        # If LLM provided a detailed narrative, append it
        if analysis.get('llm_text'):
            analysis_text += f"\n\n🧠 *Подробный разбор:*\n{analysis['llm_text']}"
        
        # Send analysis
        await bot_instance.send_message(
            user_id,
            analysis_text
        )
        
    except Exception as e:
        logger.error(f"Error sending AI analysis to {user_id}: {e}")
        # Send fallback message
        await bot_instance.send_message(
            user_id,
            "❌ Не удалось получить AI анализ. Попробуйте позже."
        )
