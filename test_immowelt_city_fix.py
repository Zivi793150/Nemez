#!/usr/bin/env python3
"""
Test script to verify Immowelt city location fixes
"""

def test_url_fixing():
    """Test URL fixing logic for different cities"""
    
    # Simulate the problematic URL from .env
    base_url = "https://www.immowelt.de/classified-search?distributionTypes=Buy,Buy_Auction&estateTypes=House,Apartment&locations=AD08DE6748"
    
    print("Testing URL fixing for different cities:")
    print("=" * 50)
    
    cities = ['Köln', 'Berlin', 'Hamburg', 'München', 'Stuttgart']
    
    for city in cities:
        print(f"\nTesting for city: {city}")
        print(f"Original URL: {base_url}")
        
        # Apply the same fixing logic as in the code
        if 'distributionTypes=Buy' in base_url or 'distributionTypes=Buy_Auction' in base_url:
            print("⚠️  URL configured for BUY, fixing to RENT")
            # Replace Buy with Rent
            fixed_url = base_url.replace('distributionTypes=Buy,Buy_Auction', 'distributionTypes=Rent')
            fixed_url = fixed_url.replace('distributionTypes=Buy', 'distributionTypes=Rent')
            
            # Fix location parameter
            if city.lower() in ['köln', 'koeln', 'cologne']:
                fixed_url = fixed_url.replace('locations=AD08DE6748', 'locations=Köln')
            elif city.lower() in ['berlin']:
                fixed_url = fixed_url.replace('locations=AD08DE6748', 'locations=Berlin')
            elif city.lower() in ['hamburg']:
                fixed_url = fixed_url.replace('locations=AD08DE6748', 'locations=Hamburg')
            elif city.lower() in ['münchen', 'muenchen', 'munich']:
                fixed_url = fixed_url.replace('locations=AD08DE6748', 'locations=München')
            elif city.lower() in ['stuttgart']:
                fixed_url = fixed_url.replace('locations=AD08DE6748', 'locations=Stuttgart')
            
            print(f"✅ Fixed URL: {fixed_url}")
        else:
            print("✅ URL is already correct for rent")

if __name__ == "__main__":
    test_url_fixing()
