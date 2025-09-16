import logging
import json
from typing import Dict, List, Optional
from config import Config
from datetime import datetime

logger = logging.getLogger(__name__)

class AIAnalyzer:
    """AI analyzer for apartment analysis"""
    
    def __init__(self):
        self.use_openai = bool(Config.OPENAI_API_KEY)
        self.use_local_model = False
        self.openai_client = None
        
        if self.use_openai:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI()
                logger.info("OpenAI client initialized for AI analysis")
            except Exception as e:
                logger.warning(f"Failed to init OpenAI client, fallback to local: {e}")
                self.use_openai = False
        if not self.use_openai:
            try:
                # Try to use local model as fallback
                self._setup_local_model()
                self.use_local_model = True
            except Exception as e:
                logger.warning(f"Could not setup local AI model: {e}")
    
    def _setup_local_model(self):
        """Setup local AI model as fallback"""
        try:
            from transformers import pipeline
            self.sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased")
            self.text_classifier = pipeline("text-classification", model="distilbert-base-uncased")
            logger.info("Local AI model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load local AI model: {e}")
            raise
    
    async def analyze_apartment(self, apartment_data: Dict, language: str = "de") -> Dict:
        """Analyze apartment and provide insights"""
        try:
            analysis = {
                "pros": [],
                "cons": [],
                "overall_score": 0,
                "recommendations": [],
                "market_analysis": {},
                "llm_text": None
            }
            
            # Analyze price competitiveness
            price_analysis = await self._analyze_price(apartment_data)
            analysis["market_analysis"]["price"] = price_analysis
            
            # Analyze location
            location_analysis = await self._analyze_location(apartment_data)
            analysis["market_analysis"]["location"] = location_analysis
            
            # Analyze property features
            features_analysis = await self._analyze_features(apartment_data)
            analysis["market_analysis"]["features"] = features_analysis
            
            # Generate pros and cons
            analysis["pros"] = await self._generate_pros(apartment_data, analysis, language)
            analysis["cons"] = await self._generate_cons(apartment_data, analysis, language)
            
            # Calculate overall score
            analysis["overall_score"] = await self._calculate_score(analysis)
            
            # Generate recommendations
            analysis["recommendations"] = await self._generate_recommendations(analysis, language)

            # If OpenAI is available, generate a detailed narrative
            if self.use_openai and self.openai_client is not None:
                analysis["llm_text"] = await self._generate_llm_analysis(apartment_data, analysis, language)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing apartment: {e}")
            return self._get_default_analysis(language)

    async def _generate_llm_analysis(self, apartment_data: Dict, analysis: Dict, language: str) -> str:
        """Generate a detailed narrative analysis using OpenAI."""
        try:
            lang_map = {
                "de": "Deutsch",
                "ru": "Русский",
                "uk": "Українська"
            }
            target_lang = lang_map.get(language, "Deutsch")
            prompt = (
                f"Ты помощник по недвижимости. Сформируй подробный разбор квартиры на {target_lang}.\n"
                f"Дай структурированный ответ с разделами:\n"
                f"1) Краткое резюме (2-3 предложения)\n"
                f"2) Плюсы (маркированный список)\n"
                f"3) Минусы (маркированный список)\n"
                f"4) Аналитика цены (упомяни цену за м² и статус: {analysis.get('market_analysis',{}).get('price',{}).get('status','unknown')})\n"
                f"5) Рекомендации (конкретные действия)\n"
                f"6) Риски/на что обратить внимание\n\n"
                f"Данные: title={apartment_data.get('title')}, city={apartment_data.get('city')}, district={apartment_data.get('district')}, "
                f"price={apartment_data.get('price')}€, area={apartment_data.get('area')}m², rooms={apartment_data.get('rooms')}.\n"
                f"Описание: {apartment_data.get('description','')[:1200]}"
            )
            resp = self.openai_client.chat.completions.create(
                model=Config.OPENAI_MODEL or "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful real estate analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=700
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI analysis failed: {e}")
            return None
    
    async def _analyze_price(self, apartment_data: Dict) -> Dict:
        """Analyze apartment price competitiveness with enhanced logic"""
        try:
            price = apartment_data.get('price', 0)
            area = apartment_data.get('area', 1)
            rooms = apartment_data.get('rooms', 1)
            city = apartment_data.get('city', '').lower()
            
            if price <= 0:
                return {"status": "unknown", "reason": "Price not available"}
            
            if area <= 0:
                # Try to estimate area from rooms if not available
                estimated_area = rooms * 25 if rooms > 0 else 50
                area = estimated_area
                analysis = {
                    "price_per_sqm": round(price / area, 2),
                    "price_per_room": round(price / rooms, 2) if rooms > 0 else 0,
                    "estimated_area": True,
                    "status": "unknown"
                }
            else:
                analysis = {
                    "price_per_sqm": round(price / area, 2),
                    "price_per_room": round(price / rooms, 2) if rooms > 0 else 0,
                    "estimated_area": False,
                    "status": "unknown"
                }
            
            # Enhanced market analysis with city-specific pricing
            price_per_sqm = analysis["price_per_sqm"]
            
            # City-specific price ranges (EUR per m²)
            city_ranges = {
                'berlin': {'very_good': 18, 'good': 22, 'fair': 28, 'expensive': 35},
                'münchen': {'very_good': 22, 'good': 28, 'fair': 35, 'expensive': 45},
                'hamburg': {'very_good': 20, 'good': 25, 'fair': 32, 'expensive': 40},
                'köln': {'very_good': 16, 'good': 20, 'fair': 26, 'expensive': 32},
                'frankfurt': {'very_good': 18, 'good': 23, 'fair': 30, 'expensive': 38},
                'stuttgart': {'very_good': 17, 'good': 22, 'fair': 28, 'expensive': 35},
                'düsseldorf': {'very_good': 19, 'good': 24, 'fair': 30, 'expensive': 38},
                'leipzig': {'very_good': 12, 'good': 16, 'fair': 20, 'expensive': 25},
                'dortmund': {'very_good': 11, 'good': 15, 'fair': 19, 'expensive': 24},
                'essen': {'very_good': 10, 'good': 14, 'fair': 18, 'expensive': 23}
            }
            
            # Get city-specific ranges or use default
            ranges = city_ranges.get(city, {'very_good': 15, 'good': 20, 'fair': 25, 'expensive': 30})
            
            if price_per_sqm <= ranges['very_good']:
                analysis["status"] = "very_good"
                analysis["reason"] = f"Excellent price for {city.title() if city else 'this location'} - below market average"
            elif price_per_sqm <= ranges['good']:
                analysis["status"] = "good"
                analysis["reason"] = f"Good price for {city.title() if city else 'this location'} - at market average"
            elif price_per_sqm <= ranges['fair']:
                analysis["status"] = "fair"
                analysis["reason"] = f"Fair price for {city.title() if city else 'this location'} - slightly above average"
            else:
                analysis["status"] = "expensive"
                analysis["reason"] = f"High price for {city.title() if city else 'this location'} - significantly above market"
            
            # Add market context
            analysis["market_context"] = {
                "city": city.title() if city else "Unknown",
                "price_range": f"{ranges['very_good']}-{ranges['expensive']}€/m²",
                "competitiveness": "high" if analysis["status"] in ["very_good", "good"] else "low"
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing price: {e}")
            return {"status": "error", "reason": "Analysis failed"}
    
    async def _analyze_location(self, apartment_data: Dict) -> Dict:
        """Analyze apartment location"""
        try:
            city = apartment_data.get('city', '').lower()
            district = apartment_data.get('district', '').lower()
            
            analysis = {
                "city": city,
                "district": district,
                "status": "unknown"
            }
            
            # Basic location analysis (enhance with real data)
            popular_cities = ['berlin', 'münchen', 'hamburg', 'köln', 'frankfurt']
            popular_districts = ['mitte', 'kreuzberg', 'neukölln', 'charlottenburg', 'prenzlauer berg']
            
            if city in popular_cities:
                analysis["status"] = "popular_city"
                analysis["reason"] = "Popular city with high demand"
                
                if district in popular_districts:
                    analysis["status"] = "premium_location"
                    analysis["reason"] = "Premium district in popular city"
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing location: {e}")
            return {"status": "error", "reason": "Analysis failed"}
    
    async def _analyze_features(self, apartment_data: Dict) -> Dict:
        """Analyze apartment features with enhanced detection"""
        try:
            features = apartment_data.get('features', [])
            if isinstance(features, str):
                try:
                    features = json.loads(features)
                except:
                    features = []
            
            # Also extract features from description
            description = apartment_data.get('description', '').lower()
            title = apartment_data.get('title', '').lower()
            text = f"{title} {description}"
            
            analysis = {
                "total_features": len(features),
                "premium_features": [],
                "basic_features": [],
                "missing_features": [],
                "detected_features": []
            }
            
            # Enhanced feature detection from text
            feature_keywords = {
                'balcony': ['balkon', 'balcony', 'terrasse', 'terrace'],
                'garden': ['garten', 'garden', 'hof', 'courtyard'],
                'parking': ['parkplatz', 'parking', 'garage', 'stellplatz'],
                'elevator': ['aufzug', 'elevator', 'lift', 'fahrstuhl'],
                'modern_kitchen': ['einbauküche', 'modern kitchen', 'neue küche', 'vollausgestattete küche'],
                'heating': ['heizung', 'heating', 'zentralheizung', 'gasheizung'],
                'internet': ['internet', 'wlan', 'wifi', 'dsl', 'glasfaser'],
                'washing_machine': ['waschmaschine', 'washing machine', 'waschkeller'],
                'dishwasher': ['geschirrspüler', 'dishwasher', 'spülmaschine'],
                'furnished': ['möbliert', 'furnished', 'vollmöbliert', 'eingerichtet'],
                'unfurnished': ['unmöbliert', 'unfurnished', 'leer'],
                'pets_allowed': ['haustiere', 'pets', 'hund', 'katze'],
                'smoking': ['rauchen', 'smoking', 'nichtraucher'],
                'floor': ['etage', 'floor', 'stockwerk', 'ebene'],
                'basement': ['keller', 'basement', 'kellerraum'],
                'attic': ['dachgeschoss', 'attic', 'dachboden']
            }
            
            # Detect features from text
            for feature, keywords in feature_keywords.items():
                if any(keyword in text for keyword in keywords):
                    analysis["detected_features"].append(feature)
            
            # Combine detected features with explicit features
            all_features = list(set(features + analysis["detected_features"]))
            
            # Define feature categories
            premium_features = ['balcony', 'terrace', 'garden', 'parking', 'elevator', 'modern_kitchen', 'furnished']
            basic_features = ['heating', 'internet', 'washing_machine', 'dishwasher', 'basement']
            
            for feature in all_features:
                feature_lower = str(feature).lower()
                if any(pf in feature_lower for pf in premium_features):
                    analysis["premium_features"].append(feature)
                elif any(bf in feature_lower for bf in basic_features):
                    analysis["basic_features"].append(feature)
            
            # Check for missing basic features
            for basic_feature in basic_features:
                if not any(basic_feature in str(f).lower() for f in all_features):
                    analysis["missing_features"].append(basic_feature)
            
            # Update total features count
            analysis["total_features"] = len(all_features)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing features: {e}")
            return {"status": "error", "reason": "Analysis failed"}
    
    async def _generate_pros(self, apartment_data: Dict, analysis: Dict, language: str) -> List[str]:
        """Generate pros for the apartment"""
        pros = []
        
        try:
            # Localized phrases
            phrases = {
                "de": {
                    "competitive_price": "💰 Wettbewerbsfähiger Preis für die Lage",
                    "excellent_location": "📍 Hervorragende Lage in einem beliebten Gebiet",
                    "premium_features": "✨ Premium‑Ausstattung: {features}",
                    "spacious": "🏠 Geräumige Wohnung mit guter Raumaufteilung",
                    "good_size": "📐 Gute Größe für die Zimmeranzahl",
                    "basic": "✅ Erfüllt grundlegende Anforderungen"
                },
                "ru": {
                    "competitive_price": "💰 Конкурентная цена для района",
                    "excellent_location": "📍 Отличная локация в популярном районе",
                    "premium_features": "✨ Премиальные особенности: {features}",
                    "spacious": "🏠 Просторная квартира с удачной планировкой",
                    "good_size": "📐 Хороший метраж для количества комнат",
                    "basic": "✅ Соответствует базовым требованиям"
                },
                "uk": {
                    "competitive_price": "💰 Конкурентна ціна для району",
                    "excellent_location": "📍 Чудова локація в популярному районі",
                    "premium_features": "✨ Преміальні особливості: {features}",
                    "spacious": "🏠 Простора квартира з вдалим плануванням",
                    "good_size": "📐 Гарний метраж для кількості кімнат",
                    "basic": "✅ Відповідає базовим вимогам"
                }
            }
            loc = phrases.get(language, phrases["de"])
            # Price pros
            price_analysis = analysis.get("market_analysis", {}).get("price", {})
            if price_analysis.get("status") in ["very_good", "good"]:
                pros.append(loc["competitive_price"])
            
            # Location pros
            location_analysis = analysis.get("market_analysis", {}).get("location", {})
            if location_analysis.get("status") in ["premium_location", "popular_city"]:
                pros.append(loc["excellent_location"])
            
            # Feature pros
            features_analysis = analysis.get("market_analysis", {}).get("features", {})
            if features_analysis.get("premium_features"):
                premium_list = features_analysis['premium_features'][:3]
                # Translate features to user language
                translated_features = []
                for feature in premium_list:
                    if feature == 'balcony':
                        translated_features.append("балкон" if language == "ru" else "балкон" if language == "uk" else "Balkon")
                    elif feature == 'furnished':
                        translated_features.append("мебель" if language == "ru" else "меблі" if language == "uk" else "Möbel")
                    elif feature == 'parking':
                        translated_features.append("парковка" if language == "ru" else "парковка" if language == "uk" else "Parkplatz")
                    else:
                        translated_features.append(feature)
                pros.append(loc["premium_features"].format(features=", ".join(translated_features)))
            
            # Size pros
            area = apartment_data.get('area', 0)
            rooms = apartment_data.get('rooms', 0)
            if area > 80 and rooms >= 3:
                pros.append(loc["spacious"])
            elif area > 50:
                pros.append(loc["good_size"])
            
            # Additional pros based on detected features
            if 'furnished' in features_analysis.get("detected_features", []):
                if language == "ru":
                    pros.append("🪑 Полностью меблированная квартира")
                elif language == "uk":
                    pros.append("🪑 Повністю мебльована квартира")
                else:
                    pros.append("🪑 Vollständig möblierte Wohnung")
            
            if 'balcony' in features_analysis.get("detected_features", []):
                if language == "ru":
                    pros.append("🌿 Есть балкон или терраса")
                elif language == "uk":
                    pros.append("🌿 Є балкон або тераса")
                else:
                    pros.append("🌿 Balkon oder Terrasse vorhanden")
            
            # Add default pros if none found
            if not pros:
                pros.append(loc["basic"])
            
        except Exception as e:
            logger.error(f"Error generating pros: {e}")
            pros = [phrases.get(language, phrases["de"]) ["basic"]]
        
        return pros
    
    async def _generate_cons(self, apartment_data: Dict, analysis: Dict, language: str) -> List[str]:
        """Generate cons for the apartment"""
        cons = []
        
        try:
            phrases = {
                "de": {
                    "expensive": "💸 Preis liegt über dem Marktdurchschnitt",
                    "missing": "❌ Fehlende Basismerkmale: {features}",
                    "small_for_rooms": "📏 Kleine Fläche für die Zimmeranzahl",
                    "very_small": "📏 Sehr kleine Wohnung",
                    "location_incomplete": "📍 Unvollständige Standortinformationen",
                    "limited": "⚠️ Begrenzte Informationen verfügbar"
                },
                "ru": {
                    "expensive": "💸 Цена выше среднего по рынку",
                    "missing": "❌ Отсутствуют базовые характеристики: {features}",
                    "small_for_rooms": "📏 Небольшая площадь для количества комнат",
                    "very_small": "📏 Очень маленькая квартира",
                    "location_incomplete": "📍 Информация о локации неполная",
                    "limited": "⚠️ Недостаточно информации"
                },
                "uk": {
                    "expensive": "💸 Ціна вища за середню на ринку",
                    "missing": "❌ Відсутні базові характеристики: {features}",
                    "small_for_rooms": "📏 Невелика площа для кількості кімнат",
                    "very_small": "📏 Дуже мала квартира",
                    "location_incomplete": "📍 Неповна інформація про локацію",
                    "limited": "⚠️ Обмежена інформація"
                }
            }
            loc = phrases.get(language, phrases["de"])
            # Price cons
            price_analysis = analysis.get("market_analysis", {}).get("price", {})
            if price_analysis.get("status") == "expensive":
                cons.append(loc["expensive"])
            
            # Feature cons
            features_analysis = analysis.get("market_analysis", {}).get("features", {})
            if features_analysis.get("missing_features"):
                cons.append(loc["missing"].format(features=", ".join(features_analysis['missing_features'][:3])))
            
            # Size cons
            area = apartment_data.get('area', 0)
            rooms = apartment_data.get('rooms', 0)
            if area < 30 and rooms > 1:
                cons.append(loc["small_for_rooms"])
            elif area < 20:
                cons.append(loc["very_small"])
            
            # Location cons
            location_analysis = analysis.get("market_analysis", {}).get("location", {})
            if not location_analysis.get("city"):
                cons.append(loc["location_incomplete"])
            
            # Add default cons if none found
            if not cons:
                cons.append(loc["limited"])
            
        except Exception as e:
            logger.error(f"Error generating cons: {e}")
            cons = [phrases.get(language, phrases["de"]) ["limited"]]
        
        return cons
    
    async def _calculate_score(self, analysis: Dict) -> int:
        """Calculate overall score (0-100)"""
        try:
            score = 50  # Base score
            
            # Price score
            price_analysis = analysis.get("market_analysis", {}).get("price", {})
            if price_analysis.get("status") == "very_good":
                score += 20
            elif price_analysis.get("status") == "good":
                score += 10
            elif price_analysis.get("status") == "expensive":
                score -= 15
            
            # Location score
            location_analysis = analysis.get("market_analysis", {}).get("location", {})
            if location_analysis.get("status") == "premium_location":
                score += 15
            elif location_analysis.get("status") == "popular_city":
                score += 10
            
            # Features score
            features_analysis = analysis.get("market_analysis", {}).get("features", {})
            if features_analysis.get("premium_features"):
                score += min(len(features_analysis["premium_features"]) * 2, 10)
            
            if features_analysis.get("missing_features"):
                score -= min(len(features_analysis["missing_features"]) * 3, 15)
            
            # Pros/Cons balance
            pros_count = len(analysis.get("pros", []))
            cons_count = len(analysis.get("cons", []))
            score += (pros_count - cons_count) * 2
            
            # Ensure score is within bounds
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error calculating score: {e}")
            return 50
    
    async def _generate_recommendations(self, analysis: Dict, language: str) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        try:
            phrases = {
                "de": {
                    "high": ["🚀 Sehr empfehlenswert – schnell handeln!", "💡 Diese Wohnung bietet ein hervorragendes Preis‑Leistungs‑Verhältnis"],
                    "good": ["✅ Gute Option – einen Blick wert", "📋 Prüfen Sie alle Details vor der Entscheidung"],
                    "medium": ["⚠️ Überlegen Sie sorgfältig – es gibt einige Punkte", "🔍 Vergleichen Sie mit anderen Optionen"],
                    "low": ["❌ Nicht empfohlen – beachten Sie andere Optionen", "💡 Wahrscheinlich gibt es bessere Angebote"],
                    "negotiate": "💰 Ziehen Sie eine Preisverhandlung in Betracht",
                    "missing": "🔧 Оцените, критичны ли отсутствующие характеристики"
                },
                "ru": {
                    "high": ["🚀 Очень рекомендуем — действуйте быстро!", "💡 Отличное соотношение цена/качество"],
                    "good": ["✅ Хороший вариант — стоит рассмотреть", "📋 Внимательно проверьте детали перед решением"],
                    "medium": ["⚠️ Подумайте внимательно — есть нюансы", "🔍 Сравните с другими вариантами"],
                    "low": ["❌ Не рекомендуем — присмотритесь к другим вариантам", "💡 Вероятно, есть предложения лучше"],
                    "negotiate": "💰 Рассмотрите возможность торга",
                    "missing": "🔧 Подумайте, критично ли отсутствие некоторых характеристик"
                },
                "uk": {
                    "high": ["🚀 Дуже рекомендуємо — дійте швидко!", "💡 Чудове співвідношення ціни та якості"],
                    "good": ["✅ Гарний варіант — варто розглянути", "📋 Уважно перевірте деталі перед рішенням"],
                    "medium": ["⚠️ Зважайте уважно — є нюанси", "🔍 Порівняйте з іншими варіантами"],
                    "low": ["❌ Не рекомендуємо — зверніть увагу на інші варіанти", "💡 Ймовірно, є кращі пропозиції"],
                    "negotiate": "💰 Розгляньте можливість торгу",
                    "missing": "🔧 Подумайте, чи критична відсутність деяких характеристик"
                }
            }
            loc = phrases.get(language, phrases["de"])
            score = analysis.get("overall_score", 50)
            
            if score >= 80:
                recommendations.extend(loc["high"])
            elif score >= 60:
                recommendations.extend(loc["good"])
            elif score >= 40:
                recommendations.extend(loc["medium"])
            else:
                recommendations.extend(loc["low"])
            
            # Specific recommendations based on analysis
            price_analysis = analysis.get("market_analysis", {}).get("price", {})
            if price_analysis.get("status") == "expensive":
                recommendations.append(loc["negotiate"])
            
            features_analysis = analysis.get("market_analysis", {}).get("features", {})
            if features_analysis.get("missing_features"):
                recommendations.append(loc["missing"])
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations = ["📋 Review all details carefully"]
        
        return recommendations
    
    def _get_default_analysis(self, language: str) -> Dict:
        """Get default analysis when AI fails"""
        return {
            "pros": ["✅ Meets basic requirements"],
            "cons": ["⚠️ Limited information available"],
            "overall_score": 50,
            "recommendations": ["📋 Review all details carefully"],
            "market_analysis": {
                "price": {"status": "unknown", "reason": "Analysis unavailable"},
                "location": {"status": "unknown", "reason": "Analysis unavailable"},
                "features": {"status": "unknown", "reason": "Analysis unavailable"}
            }
        }

# Global AI analyzer instance
ai_analyzer = AIAnalyzer()

async def analyze_apartment_ai(apartment_data: Dict, language: str = "de") -> Dict:
    """Analyze apartment using AI (async wrapper)"""
    return await ai_analyzer.analyze_apartment(apartment_data, language)
