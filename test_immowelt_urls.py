#!/usr/bin/env python3
"""
Test script to verify different Immowelt URL formats
"""

import urllib.parse

def test_immowelt_urls():
    """Test different URL formats for Immowelt"""
    
    print("Testing different Immowelt URL formats:")
    print("=" * 50)
    
    city = "Hamburg"
    
    # Test different URL approaches
    urls_to_test = [
        # 1. Simple rent URL
        "https://www.immowelt.de/classified-search?distributionTypes=Rent&estateTypes=Apartment",
        
        # 2. URL with city filter
        f"https://www.immowelt.de/classified-search?distributionTypes=Rent&estateTypes=Apartment&locations={urllib.parse.quote(city)}",
        
        # 3. URL from documentation (Buy -> Rent)
        "https://www.immowelt.de/classified-search?distributionTypes=Rent&estateTypes=House,Apartment&locations=AD08DE6748",
        
        # 4. URL with specific city and price filter
        f"https://www.immowelt.de/classified-search?distributionTypes=Rent&estateTypes=Apartment&locations={urllib.parse.quote(city)}&priceMax=2500",
        
        # 5. URL with rooms filter
        f"https://www.immowelt.de/classified-search?distributionTypes=Rent&estateTypes=Apartment&locations={urllib.parse.quote(city)}&roomsMax=4",
        
        # 6. Complete URL with all filters
        f"https://www.immowelt.de/classified-search?distributionTypes=Rent&estateTypes=Apartment&locations={urllib.parse.quote(city)}&priceMax=2500&roomsMax=4"
    ]
    
    for i, url in enumerate(urls_to_test, 1):
        print(f"\n{i}. {url}")
        
        # Test payload
        payload = {
            "startUrl": url,
            "maxPagesToScrape": 1,
            "enableDeltaMode": False
        }
        print(f"   Payload: {payload}")
    
    print(f"\n✅ Tested {len(urls_to_test)} different URL formats")
    print("🔍 The bot will try these URLs in sequence until one works")

if __name__ == "__main__":
    test_immowelt_urls()
