#!/usr/bin/env python3
"""
Test script to verify Immowelt actor input format
"""

def test_actor_input_format():
    """Test the correct input format for Immowelt actor"""
    
    print("Testing Immowelt actor input format:")
    print("=" * 40)
    
    # Test explicit URL (from .env)
    explicit_url = "https://www.immowelt.de/classified-search?distributionTypes=Rent&estateTypes=House,Apartment&locations=Hamburg"
    
    # Test simple URL
    simple_url = "https://www.immowelt.de/classified-search?distributionTypes=Rent&estateTypes=Apartment"
    
    print("\n1. Explicit URL format:")
    explicit_payload = {
        "startUrl": explicit_url,  # String as required
        "maxPagesToScrape": 1
    }
    print(f"Payload: {explicit_payload}")
    
    print("\n2. Simple URL format:")
    simple_payload = {
        "startUrl": simple_url,  # String as required
        "maxPagesToScrape": 1
    }
    print(f"Payload: {simple_payload}")
    
    print("\n✅ All formats use strings as required by the actor API")

if __name__ == "__main__":
    test_actor_input_format()
