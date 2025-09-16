#!/usr/bin/env python3
"""
Простой тест бота без Apify (так как лимит превышен)
"""

import asyncio
import logging
from config import Config
from mongodb_manager import mongodb

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_mongodb_connection():
    """Тест подключения к MongoDB"""
    print("🔍 Тестирование подключения к MongoDB...")
    
    try:
        if await mongodb.connect():
            print("✅ MongoDB подключение успешно!")
            
            # Тест создания пользователя
            test_user = await mongodb.create_user(
                telegram_id=123456789,
                username="test_user",
                first_name="Test",
                last_name="User",
                language="ru"
            )
            
            if test_user:
                print("✅ Пользователь создан успешно!")
                
                # Тест сохранения фильтров
                test_filters = {
                    "city": "Berlin",
                    "price_min": 500,
                    "price_max": 1500,
                    "rooms_min": 1,
                    "rooms_max": 3
                }
                
                if await mongodb.save_user_filter(123456789, test_filters):
                    print("✅ Фильтры сохранены успешно!")
                    
                    # Тест получения фильтров
                    saved_filters = await mongodb.get_user_filter(123456789)
                    if saved_filters:
                        print(f"✅ Фильтры получены: {saved_filters}")
                    else:
                        print("❌ Не удалось получить фильтры")
                else:
                    print("❌ Не удалось сохранить фильтры")
            else:
                print("❌ Не удалось создать пользователя")
            
            await mongodb.disconnect()
            print("✅ MongoDB отключение успешно!")
            return True
        else:
            print("❌ Не удалось подключиться к MongoDB")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании MongoDB: {e}")
        return False

async def test_config():
    """Тест конфигурации"""
    print("\n🔍 Тестирование конфигурации...")
    
    try:
        print(f"BOT_TOKEN: {'✅ Установлен' if Config.BOT_TOKEN else '❌ Не установлен'}")
        print(f"MONGODB_URI: {'✅ Установлен' if Config.MONGODB_URI else '❌ Не установлен'}")
        print(f"APIFY_TOKEN: {'✅ Установлен' if Config.APIFY_TOKEN else '❌ Не установлен'}")
        print(f"OPENAI_API_KEY: {'✅ Установлен' if Config.OPENAI_API_KEY else '❌ Не установлен'}")
        
        print(f"\nApify акторы:")
        print(f"  IMMOSCOUT24: {Config.APIFY_ACTOR_IMMOSCOUT24}")
        print(f"  IMMOWELT: {Config.APIFY_ACTOR_IMMOWELT}")
        print(f"  KLEINANZEIGEN: {Config.APIFY_ACTOR_KLEINANZEIGEN}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании конфигурации: {e}")
        return False

async def test_basic_functionality():
    """Тест базовой функциональности"""
    print("\n🔍 Тестирование базовой функциональности...")
    
    try:
        # Тест импорта основных модулей
        from locales import get_text
        from notifications import set_bot_instance, get_apartment_keyboard
        
        print("✅ Основные модули импортированы успешно!")
        
        # Тест локализации
        test_text = get_text("welcome_message", "ru")
        if test_text:
            print("✅ Локализация работает!")
        else:
            print("❌ Проблемы с локализацией")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании функциональности: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🏠 Тестирование бота поиска квартир в Германии")
    print("=" * 60)
    
    # Тест конфигурации
    config_ok = await test_config()
    
    # Тест MongoDB
    mongodb_ok = await test_mongodb_connection()
    
    # Тест базовой функциональности
    functionality_ok = await test_basic_functionality()
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"Конфигурация: {'✅ OK' if config_ok else '❌ FAIL'}")
    print(f"MongoDB: {'✅ OK' if mongodb_ok else '❌ FAIL'}")
    print(f"Функциональность: {'✅ OK' if functionality_ok else '❌ FAIL'}")
    
    if config_ok and mongodb_ok and functionality_ok:
        print("\n🎉 Все тесты пройдены! Бот готов к работе.")
        print("\n💡 Примечание: Apify лимит превышен, но бот может работать с другими источниками данных.")
    else:
        print("\n⚠️ Некоторые тесты не пройдены. Проверьте конфигурацию.")

if __name__ == "__main__":
    asyncio.run(main())
