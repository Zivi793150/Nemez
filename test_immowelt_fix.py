#!/usr/bin/env python3
"""
Test script to verify Immowelt parsing fixes
"""

import asyncio
import logging
from real_api_system import RealEstateAPI

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_immowelt_parsing():
    """Test Immowelt parsing with different cities"""
    
    async with RealEstateAPI() as api:
        # Test filters for Köln
        filters_koeln = {
            'city': 'Köln',
            'price_max': 3000,
            'rooms_max': 4
        }
        
        logger.info("Testing Immowelt parsing for Köln...")
        apartments = await api._search_apify_immowelt(filters_koeln)
        
        logger.info(f"Found {len(apartments)} apartments for Köln")
        
        # Check if we got apartments from the right city
        for apt in apartments[:3]:  # Show first 3
            logger.info(f"Apartment: {apt.get('title', 'No title')} - {apt.get('city', 'No city')} - {apt.get('price', 0)}€")
        
        # Test filters for Berlin
        filters_berlin = {
            'city': 'Berlin',
            'price_max': 2000,
            'rooms_max': 3
        }
        
        logger.info("\nTesting Immowelt parsing for Berlin...")
        apartments_berlin = await api._search_apify_immowelt(filters_berlin)
        
        logger.info(f"Found {len(apartments_berlin)} apartments for Berlin")
        
        # Check if we got apartments from the right city
        for apt in apartments_berlin[:3]:  # Show first 3
            logger.info(f"Apartment: {apt.get('title', 'No title')} - {apt.get('city', 'No city')} - {apt.get('price', 0)}€")

if __name__ == "__main__":
    asyncio.run(test_immowelt_parsing())
