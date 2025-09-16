#!/usr/bin/env python3
"""
Test script to verify Immowelt parsing improvements
"""

def test_parsing_logic():
    """Test the improved parsing logic"""
    
    # Simulate Immowelt data structure
    test_item = {
        'hardFacts': {
            'price': {
                'value': '1.500 €',
                'formatted': '1.500 €'
            },
            'keyfacts': ['2 Zimmer', '65 m²', 'frei ab 01.01.2025'],
            'facts': [
                {'type': 'numberOfRooms', 'value': '2 Zimmer', 'splitValue': '2'},
                {'type': 'livingSpace', 'value': '65 m²', 'splitValue': '65'}
            ]
        },
        'rawData': {
            'price': 1500,
            'nbroom': 2,
            'surface': {'main': 65}
        }
    }
    
    print("Testing Immowelt parsing logic:")
    print("=" * 40)
    
    # Test price parsing
    print("\n1. Testing price parsing:")
    hard_facts = test_item.get('hardFacts', {})
    
    # Test hardFacts price
    if 'price' in hard_facts:
        price_data = hard_facts['price']
        if isinstance(price_data, dict):
            price = to_float(price_data.get('value')) or to_float(price_data.get('formatted'))
            if price and price > 0:
                print(f"✅ Found price from hardFacts: {price}€")
    
    # Test keyfacts price
    if 'keyfacts' in hard_facts:
        keyfacts = hard_facts.get('keyfacts', [])
        for fact in keyfacts:
            if isinstance(fact, str) and '€' in fact:
                price = to_float(fact)
                if price and price > 0:
                    print(f"✅ Found price from keyfacts: {price}€")
                    break
    
    # Test rawData price
    if 'rawData' in test_item:
        raw_data = test_item.get('rawData', {})
        if 'price' in raw_data:
            price = to_float(raw_data['price'])
            if price and price > 0:
                print(f"✅ Found price from rawData: {price}€")
    
    # Test rooms parsing
    print("\n2. Testing rooms parsing:")
    
    # Test hardFacts rooms
    if 'facts' in hard_facts:
        for fact in hard_facts['facts']:
            if isinstance(fact, dict) and fact.get('type') == 'numberOfRooms':
                rooms = to_float(fact.get('splitValue'))
                if rooms and rooms > 0:
                    print(f"✅ Found rooms from hardFacts: {rooms}")
                    break
    
    # Test keyfacts rooms
    if 'keyfacts' in hard_facts:
        keyfacts = hard_facts.get('keyfacts', [])
        for fact in keyfacts:
            if isinstance(fact, str) and ('Zimmer' in fact or 'Zi.' in fact):
                rooms = to_float(fact)
                if rooms and rooms > 0:
                    print(f"✅ Found rooms from keyfacts: {rooms}")
                    break
    
    # Test rawData rooms
    if 'rawData' in test_item:
        raw_data = test_item.get('rawData', {})
        if 'nbroom' in raw_data:
            rooms = to_float(raw_data['nbroom'])
            if rooms and rooms > 0:
                print(f"✅ Found rooms from rawData: {rooms}")
    
    # Test area parsing
    print("\n3. Testing area parsing:")
    
    # Test hardFacts area
    if 'facts' in hard_facts:
        for fact in hard_facts['facts']:
            if isinstance(fact, dict) and fact.get('type') == 'livingSpace':
                area = to_float(fact.get('splitValue'))
                if area and area > 0:
                    print(f"✅ Found area from hardFacts: {area}m²")
                    break
    
    # Test keyfacts area
    if 'keyfacts' in hard_facts:
        keyfacts = hard_facts.get('keyfacts', [])
        for fact in keyfacts:
            if isinstance(fact, str) and ('m²' in fact or 'qm' in fact):
                area = to_float(fact)
                if area and area > 0:
                    print(f"✅ Found area from keyfacts: {area}m²")
                    break
    
    # Test rawData area
    if 'rawData' in test_item:
        raw_data = test_item.get('rawData', {})
        if 'surface' in raw_data:
            surface = raw_data['surface']
            if isinstance(surface, dict) and 'main' in surface:
                area = to_float(surface['main'])
                if area and area > 0:
                    print(f"✅ Found area from rawData: {area}m²")

def to_float(v):
    """Helper function to convert string to float"""
    try:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            import re
            m = re.search(r"([0-9][0-9\.,\s]*)", v)
            if m:
                return float(m.group(1).replace(".", "").replace(" ", "").replace(",", "."))
    except Exception:
        return None
    return None

if __name__ == "__main__":
    test_parsing_logic()
