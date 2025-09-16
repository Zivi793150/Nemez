#!/usr/bin/env python3
"""
Тест разных location ID для Immowelt
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from real_api_system import RealEstateAPI

async def test_immowelt_locations():
    """Тестируем разные location ID для Immowelt"""
    
    # Initialize the API system
    api = RealEstateAPI()
    
    # Test different location approaches for Hamburg
    test_urls = [
        # 1. Direct city name
        "https://www.immowelt.de/classified-search?distributionTypes=Rent&estateTypes=Apartment&locations=Hamburg",
        
        # 2. URL encoded city name
        "https://www.immowelt.de/classified-search?distributionTypes=Rent&estateTypes=Apartment&locations=Hamburg",
        
        # 3. Different location ID (try some common ones)
        "https://www.immowelt.de/classified-search?distributionTypes=Rent&estateTypes=Apartment&locations=AD08DE6748",  # Current (Kolbermoor)
        
        # 4. Try without location parameter
        "https://www.immowelt.de/classified-search?distributionTypes=Rent&estateTypes=Apartment",
        
        # 5. Try with different location ID format
        "https://www.immowelt.de/classified-search?distributionTypes=Rent&estateTypes=Apartment&locations=Hamburg%2C%20Deutschland",
    ]
    
    print("🔍 Тестируем разные URL для Immowelt Hamburg...")
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n--- Тест {i}: {url} ---")
        
        try:
            # Test with Apify
            actor_id = "azzouzana~immowelt-de-search-results-scraper-by-search-url"
            test_payload = {
                "startUrl": url,
                "maxPagesToScrape": 1,
                "enableDeltaMode": False
            }
            
            items = await api._start_apify_run_sync_get_items(actor_id, test_payload, source_name='immowelt')
            
            if items:
                print(f"✅ Найдено {len(items)} квартир")
                
                # Check cities in results
                cities = set()
                for item in items[:3]:  # Check first 3 items
                    if 'location' in item and 'address' in item['location']:
                        city = item['location']['address'].get('city', 'Unknown')
                        cities.add(city)
                        print(f"  - Город: {city}")
                
                print(f"  - Уникальные города: {list(cities)}")
                
                # Check if any Hamburg apartments
                hamburg_found = any('hamburg' in city.lower() for city in cities)
                if hamburg_found:
                    print("  🎉 НАЙДЕНЫ КВАРТИРЫ В HAMBURG!")
                else:
                    print("  ❌ Квартиры в Hamburg не найдены")
            else:
                print("❌ Квартиры не найдены")
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    print("\n🏁 Тестирование завершено")

if __name__ == "__main__":
    asyncio.run(test_immowelt_locations())
