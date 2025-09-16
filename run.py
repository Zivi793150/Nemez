#!/usr/bin/env python3
"""
Скрипт для запуска бота поиска квартир
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

def check_environment():
    """Проверка переменных окружения"""
    print("🔍 Проверка конфигурации...")
    
    # Проверяем наличие .env файла
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  Файл .env не найден!")
        print("📝 Создайте файл .env на основе env_example.txt")
        print("   cp env_example.txt .env")
        return False
    
    # Загружаем переменные окружения из .env файла
    from dotenv import load_dotenv
    load_dotenv()
    
    # Проверяем BOT_TOKEN
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token or bot_token == "your_bot_token_here":
        print("❌ BOT_TOKEN не настроен!")
        print("📝 Добавьте ваш токен в файл .env")
        print("   BOT_TOKEN=your_actual_token_here")
        return False
    
    print("✅ Конфигурация проверена")
    return True

def check_dependencies():
    """Проверка зависимостей"""
    print("📦 Проверка зависимостей...")
    
    try:
        import aiogram
        import aiohttp
        import motor
        import pymongo
        import bs4  # beautifulsoup4 импортируется как bs4
        print("✅ Все зависимости установлены")
        return True
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("📦 Установите зависимости:")
        print("   pip install -r requirements.txt")
        return False

def create_directories():
    """Создание необходимых директорий"""
    directories = ["data", "logs"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("📁 Директории созданы")

async def main():
    """Основная функция"""
    print("🏠 Запуск бота поиска квартир в Германии")
    print("=" * 50)
    
    # Проверки
    if not check_environment():
        sys.exit(1)
    
    if not check_dependencies():
        sys.exit(1)
    
    create_directories()
    
    print("\n🚀 Запуск бота...")
    print("💡 Для остановки нажмите Ctrl+C")
    print("=" * 50)
    
    try:
        # Импортируем и запускаем бота
        from bot import main as bot_main
        await bot_main()
    except KeyboardInterrupt:
        print("\n⏹️  Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка запуска бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
