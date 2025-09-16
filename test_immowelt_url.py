#!/usr/bin/env python3
"""
Test script to verify Immowelt URL generation
"""

import urllib.parse

def test_url_generation():
    """Test URL generation for different cities"""
    
    print("Testing Immowelt URL generation:")
    print("=" * 40)
    
    cities = ['Hamburg', 'Berlin', 'Köln', 'München', 'Stuttgart', 'Düsseldorf']
    
    for city in cities:
        print(f"\nTesting for city: {city}")
        
        # Build URL like in the code
        base_url = "https://www.immowelt.de/classified-search"
        params = [
            "distributionTypes=Rent",
            "estateTypes=Apartment"
        ]
        
        # Add location with URL encoding
        if city.lower() in ['köln', 'koeln', 'cologne']:
            params.append(f"locations={urllib.parse.quote('Köln')}")
        elif city.lower() in ['berlin']:
            params.append(f"locations={urllib.parse.quote('Berlin')}")
        elif city.lower() in ['hamburg']:
            params.append(f"locations={urllib.parse.quote('Hamburg')}")
        elif city.lower() in ['münchen', 'muenchen', 'munich']:
            params.append(f"locations={urllib.parse.quote('München')}")
        elif city.lower() in ['stuttgart']:
            params.append(f"locations={urllib.parse.quote('Stuttgart')}")
        elif city.lower() in ['düsseldorf', 'duesseldorf', 'dusseldorf']:
            params.append(f"locations={urllib.parse.quote('Düsseldorf')}")
        else:
            params.append(f"locations={urllib.parse.quote(city)}")
        
        # Add price and room filters
        params.append("priceMax=2500")
        params.append("roomsMax=4")
        
        full_url = base_url + "?" + "&".join(params)
        print(f"Full URL: {full_url}")
        
        # Test simple URL
        simple_url = "https://www.immowelt.de/classified-search?distributionTypes=Rent&estateTypes=Apartment"
        print(f"Simple URL: {simple_url}")

if __name__ == "__main__":
    test_url_generation()
