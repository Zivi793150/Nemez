#!/usr/bin/env python3
"""
Тест поиска квартир с настоящими объявлениями
"""

import asyncio
import logging
from config import Config
from mongodb_manager import mongodb
from real_api_system import RealEstateAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_apartment_search():
    """Тест поиска квартир"""
    print("🏠 Тестирование поиска квартир...")
    
    try:
        # Подключаемся к MongoDB
        if not await mongodb.connect():
            print("❌ Не удалось подключиться к MongoDB")
            return False
        
        # Создаем тестовые фильтры
        test_filters = {
            "city": "Berlin",
            "price_min": 500,
            "price_max": 1500,
            "rooms_min": 1,
            "rooms_max": 3
        }
        
        print(f"🔍 Поиск квартир с фильтрами: {test_filters}")
        
        # Используем RealEstateAPI для поиска
        async with RealEstateAPI() as api:
            apartments = await api.search_apartments(test_filters)
            
            print(f"✅ Найдено {len(apartments)} квартир!")
            
            if apartments:
                print("\n📋 Первые 3 квартиры:")
                for i, apt in enumerate(apartments[:3], 1):
                    print(f"\n{i}. {apt.get('title', 'Без названия')}")
                    print(f"   💰 Цена: {apt.get('price', 0)}€")
                    print(f"   🏠 Комнаты: {apt.get('rooms', 0)}")
                    print(f"   📐 Площадь: {apt.get('area', 0)}м²")
                    print(f"   📍 Город: {apt.get('city', 'Не указан')}")
                    print(f"   🔗 URL: {apt.get('original_url', 'Нет ссылки')}")
                
                # Сохраняем квартиры в базу данных
                print(f"\n💾 Сохраняем {len(apartments)} квартир в базу данных...")
                saved_count = 0
                for apt in apartments:
                    apt_id = await mongodb.save_apartment(apt)
                    if apt_id:
                        saved_count += 1
                
                print(f"✅ Сохранено {saved_count} квартир в базу данных!")
                
                # Тестируем поиск из базы данных
                print(f"\n🔍 Поиск квартир из базы данных...")
                db_apartments = await mongodb.get_apartments_by_filters(test_filters, limit=5)
                print(f"✅ Найдено {len(db_apartments)} квартир в базе данных!")
                
                if db_apartments:
                    print("\n📋 Квартиры из базы данных:")
                    for i, apt in enumerate(db_apartments[:3], 1):
                        print(f"\n{i}. {apt.get('title', 'Без названия')}")
                        print(f"   💰 Цена: {apt.get('price', 0)}€")
                        print(f"   🏠 Комнаты: {apt.get('rooms', 0)}")
                        print(f"   📐 Площадь: {apt.get('area', 0)}м²")
                        print(f"   📍 Город: {apt.get('city', 'Не указан')}")
                        print(f"   🔗 URL: {apt.get('original_url', 'Нет ссылки')}")
            else:
                print("❌ Квартиры не найдены")
                return False
        
        await mongodb.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при поиске квартир: {e}")
        logger.error(f"Error in apartment search: {e}")
        return False

async def test_direct_scrapers():
    """Тест прямых скраперов"""
    print("\n🔍 Тестирование прямых скраперов...")
    
    try:
        from scrapers import ScraperManager
        
        test_filters = {
            "city": "Berlin",
            "price_min": 500,
            "price_max": 1500,
            "rooms_min": 1,
            "rooms_max": 3
        }
        
        async with ScraperManager() as sm:
            apartments = await sm.search_all_sites(test_filters)
            
            print(f"✅ Прямые скраперы нашли {len(apartments)} квартир!")
            
            if apartments:
                print("\n📋 Первые 2 квартиры от прямых скраперов:")
                for i, apt in enumerate(apartments[:2], 1):
                    print(f"\n{i}. {apt.get('title', 'Без названия')}")
                    print(f"   💰 Цена: {apt.get('price', 0)}€")
                    print(f"   🏠 Комнаты: {apt.get('rooms', 0)}")
                    print(f"   📐 Площадь: {apt.get('area', 0)}м²")
                    print(f"   📍 Город: {apt.get('city', 'Не указан')}")
                    print(f"   🔗 URL: {apt.get('original_url', 'Нет ссылки')}")
            
            return len(apartments) > 0
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании прямых скраперов: {e}")
        logger.error(f"Error in direct scrapers test: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🏠 Тестирование поиска квартир с настоящими объявлениями")
    print("=" * 70)
    
    # Тест поиска квартир через API
    api_search_ok = await test_apartment_search()
    
    # Тест прямых скраперов
    scrapers_ok = await test_direct_scrapers()
    
    print("\n" + "=" * 70)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ПОИСКА:")
    print(f"API поиск: {'✅ OK' if api_search_ok else '❌ FAIL'}")
    print(f"Прямые скраперы: {'✅ OK' if scrapers_ok else '❌ FAIL'}")
    
    if api_search_ok or scrapers_ok:
        print("\n🎉 Поиск квартир работает! Бот готов показывать настоящие объявления.")
        print("\n💡 Теперь можно запустить бота командой: python run.py")
    else:
        print("\n⚠️ Поиск квартир не работает. Проверьте настройки.")

if __name__ == "__main__":
    asyncio.run(main())
