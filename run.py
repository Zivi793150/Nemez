#!/usr/bin/env python3
"""
Simple script to run the web application
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Main function to run the web application"""
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ Error: .env file not found!")
        print("📝 Please copy env_web_example.txt to .env and configure it")
        print("💡 Example: cp env_web_example.txt .env")
        sys.exit(1)
    
    # Get settings from environment
    host = os.getenv('WEB_HOST', '0.0.0.0')
    port = int(os.getenv('WEB_PORT', 8000))
    debug = os.getenv('DEBUG', 'true').lower() == 'true'
    reload = debug
    
    print("🚀 Starting German Apartment Finder Web Application...")
    print(f"📍 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"🐛 Debug: {debug}")
    print(f"🔄 Reload: {reload}")
    print()
    print("🌐 Open your browser and go to:")
    print(f"   http://localhost:{port}")
    print()
    print("📚 API Documentation:")
    print(f"   http://localhost:{port}/docs")
    print()
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        # Run the application
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
