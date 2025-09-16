#!/usr/bin/env python3
"""
Apartment Caching System
Система кэширования объявлений для избежания дублирования
"""

import json
import logging
import time
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta

import redis
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()

class ApartmentCache(Base):
    """Модель для кэширования объявлений"""
    __tablename__ = 'apartment_cache'
    
    external_id = Column(String(255), primary_key=True)
    source = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    price = Column(Integer)
    city = Column(String(100))
    district = Column(String(100))
    rooms = Column(Integer)
    area = Column(Integer)
    original_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    data = Column(Text)  # JSON с полными данными
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            'external_id': self.external_id,
            'source': self.source,
            'title': self.title,
            'price': self.price,
            'city': self.city,
            'district': self.district,
            'rooms': self.rooms,
            'area': self.area,
            'original_url': self.original_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'data': json.loads(self.data) if self.data else {}
        }

class ApartmentCacheManager:
    """Менеджер кэша объявлений"""
    
    def __init__(self, db_url: str = "sqlite:///apartment_cache.db", redis_url: str = "redis://localhost:6379"):
        self.db_url = db_url
        self.redis_url = redis_url
        
        # Инициализация базы данных
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Инициализация Redis
        try:
            self.redis_client = redis.from_url(redis_url)
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory cache.")
            self.redis_client = None
        
        # In-memory cache для fallback
        self.memory_cache = {}
        self.memory_cache_ttl = 3600  # 1 час
    
    def get_cached_apartments(self, source: Optional[str] = None, city: Optional[str] = None) -> List[Dict]:
        """Получение кэшированных объявлений"""
        try:
            query = self.session.query(ApartmentCache)
            
            if source:
                query = query.filter(ApartmentCache.source == source)
            if city:
                query = query.filter(ApartmentCache.city == city)
            
            # Только объявления, которые видели в последние 7 дней
            week_ago = datetime.utcnow() - timedelta(days=7)
            query = query.filter(ApartmentCache.last_seen >= week_ago)
            
            apartments = query.all()
            return [apt.to_dict() for apt in apartments]
            
        except Exception as e:
            logger.error(f"Error getting cached apartments: {e}")
            return []
    
    def get_new_apartments(self, apartments: List[Dict]) -> List[Dict]:
        """Фильтрация новых объявлений"""
        new_apartments = []
        
        try:
            # Получаем существующие ID
            existing_ids = self._get_existing_ids()
            
            for apartment in apartments:
                external_id = apartment.get('external_id')
                if external_id and external_id not in existing_ids:
                    new_apartments.append(apartment)
                    
        except Exception as e:
            logger.error(f"Error filtering new apartments: {e}")
            return apartments  # Возвращаем все, если ошибка
        
        return new_apartments
    
    def cache_apartments(self, apartments: List[Dict]) -> int:
        """Кэширование объявлений"""
        cached_count = 0
        
        try:
            for apartment in apartments:
                external_id = apartment.get('external_id')
                if not external_id:
                    continue
                
                # Проверяем, существует ли уже
                existing = self.session.query(ApartmentCache).filter(
                    ApartmentCache.external_id == external_id
                ).first()
                
                if existing:
                    # Обновляем last_seen
                    existing.last_seen = datetime.utcnow()
                    existing.data = json.dumps(apartment)
                else:
                    # Создаем новое
                    cache_entry = ApartmentCache(
                        external_id=external_id,
                        source=apartment.get('source', 'unknown'),
                        title=apartment.get('title', ''),
                        price=apartment.get('price'),
                        city=apartment.get('city'),
                        district=apartment.get('district'),
                        rooms=apartment.get('rooms'),
                        area=apartment.get('area'),
                        original_url=apartment.get('original_url'),
                        data=json.dumps(apartment)
                    )
                    self.session.add(cache_entry)
                
                cached_count += 1
            
            self.session.commit()
            
            # Обновляем Redis кэш
            if self.redis_client:
                self._update_redis_cache(apartments)
            
        except Exception as e:
            logger.error(f"Error caching apartments: {e}")
            self.session.rollback()
        
        return cached_count
    
    def _get_existing_ids(self) -> Set[str]:
        """Получение существующих ID из кэша"""
        try:
            if self.redis_client:
                # Пробуем получить из Redis
                cached_ids = self.redis_client.smembers('apartment_ids')
                if cached_ids:
                    return {id.decode('utf-8') for id in cached_ids}
            
            # Fallback к базе данных
            apartments = self.session.query(ApartmentCache.external_id).all()
            return {apt.external_id for apt in apartments}
            
        except Exception as e:
            logger.error(f"Error getting existing IDs: {e}")
            return set()
    
    def _update_redis_cache(self, apartments: List[Dict]):
        """Обновление Redis кэша"""
        try:
            if not self.redis_client:
                return
            
            # Добавляем новые ID
            new_ids = [apt.get('external_id') for apt in apartments if apt.get('external_id')]
            if new_ids:
                self.redis_client.sadd('apartment_ids', *new_ids)
            
            # Кэшируем данные объявлений
            for apartment in apartments:
                external_id = apartment.get('external_id')
                if external_id:
                    key = f"apartment:{external_id}"
                    self.redis_client.setex(
                        key, 
                        self.memory_cache_ttl, 
                        json.dumps(apartment)
                    )
                    
        except Exception as e:
            logger.error(f"Error updating Redis cache: {e}")
    
    def get_apartment_stats(self) -> Dict:
        """Получение статистики кэша"""
        try:
            total_count = self.session.query(ApartmentCache).count()
            
            # По источникам
            sources = self.session.query(
                ApartmentCache.source, 
                self.session.query(ApartmentCache).filter(
                    ApartmentCache.source == ApartmentCache.source
                ).count()
            ).group_by(ApartmentCache.source).all()
            
            # По городам
            cities = self.session.query(
                ApartmentCache.city, 
                self.session.query(ApartmentCache).filter(
                    ApartmentCache.city == ApartmentCache.city
                ).count()
            ).group_by(ApartmentCache.city).all()
            
            # Новые за последние 24 часа
            day_ago = datetime.utcnow() - timedelta(days=1)
            new_today = self.session.query(ApartmentCache).filter(
                ApartmentCache.created_at >= day_ago
            ).count()
            
            return {
                'total_apartments': total_count,
                'new_today': new_today,
                'by_source': {source: count for source, count in sources},
                'by_city': {city: count for city, count in cities if city}
            }
            
        except Exception as e:
            logger.error(f"Error getting apartment stats: {e}")
            return {}
    
    def cleanup_old_apartments(self, days: int = 30):
        """Очистка старых объявлений"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted_count = self.session.query(ApartmentCache).filter(
                ApartmentCache.last_seen < cutoff_date
            ).delete()
            
            self.session.commit()
            
            logger.info(f"Cleaned up {deleted_count} old apartments")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old apartments: {e}")
            self.session.rollback()
            return 0
    
    def close(self):
        """Закрытие соединений"""
        if self.session:
            self.session.close()
        if self.redis_client:
            self.redis_client.close()

# Глобальный экземпляр кэша
cache_manager = None

def get_cache_manager() -> ApartmentCacheManager:
    """Получение глобального экземпляра кэша"""
    global cache_manager
    if cache_manager is None:
        cache_manager = ApartmentCacheManager()
    return cache_manager

def cleanup_cache():
    """Очистка кэша"""
    global cache_manager
    if cache_manager:
        cache_manager.close()
        cache_manager = None
