#!/usr/bin/env python3
"""
Test script to verify URL fixing logic
"""

def test_url_fixing():
    """Test URL fixing logic"""
    
    # Simulate the problematic URL from .env
    problematic_url = "https://www.immowelt.de/classified-search?distributionTypes=Buy,Buy_Auction&estateTypes=House,Apartment&locations=AD08DE6748"
    
    print(f"Original URL: {problematic_url}")
    
    # Apply the same fixing logic as in the code
    if 'distributionTypes=Buy' in problematic_url or 'distributionTypes=Buy_Auction' in problematic_url:
        print("⚠️  URL configured for BUY, fixing to RENT")
        # Replace Buy with Rent
        fixed_url = problematic_url.replace('distributionTypes=Buy,Buy_Auction', 'distributionTypes=Rent')
        fixed_url = fixed_url.replace('distributionTypes=Buy', 'distributionTypes=Rent')
        print(f"✅ Fixed URL: {fixed_url}")
    else:
        print("✅ URL is already correct for rent")
    
    # Test city matching logic
    print("\n--- Testing city matching logic ---")
    
    test_cases = [
        ('Köln', 'Köln', True),
        ('Köln', 'koeln', True), 
        ('Köln', 'cologne', True),
        ('Köln', 'Kolbermoor', False),
        ('Berlin', 'Berlin', True),
        ('Hamburg', 'Hamburg', True),
    ]
    
    for filter_city, apartment_city, expected in test_cases:
        filter_city_lower = filter_city.lower()
        apartment_city_lower = apartment_city.lower()
        
        # Apply the same matching logic as in the code
        city_matches = (
            filter_city_lower in apartment_city_lower or 
            apartment_city_lower in filter_city_lower or
            # Handle common city name variations
            (filter_city_lower == 'köln' and apartment_city_lower in ['köln', 'koeln', 'cologne']) or
            (filter_city_lower == 'koeln' and apartment_city_lower in ['köln', 'koeln', 'cologne']) or
            (filter_city_lower == 'cologne' and apartment_city_lower in ['köln', 'koeln', 'cologne']) or
            (filter_city_lower == 'berlin' and apartment_city_lower == 'berlin') or
            (filter_city_lower == 'hamburg' and apartment_city_lower == 'hamburg')
        )
        
        status = "✅" if city_matches == expected else "❌"
        print(f"{status} Filter: {filter_city} | Apartment: {apartment_city} | Expected: {expected} | Got: {city_matches}")

if __name__ == "__main__":
    test_url_fixing()
