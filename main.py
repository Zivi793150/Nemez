#!/usr/bin/env python3
"""
German Apartment Finder - Web Application
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config.settings import get_settings
from app.database.init_db import init_database
from app.api.routes import api_router
from app.core.middleware import LoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🚀 Starting German Apartment Finder Web Application...")
    
    # Initialize database
    await init_database()
    print("✅ Database initialized")
    
    # Start background services
    # await start_background_services()
    print("✅ Background services started")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down application...")


# Create FastAPI app
app = FastAPI(
    title="German Apartment Finder",
    description="Web application for finding apartments in Germany",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(LoggingMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="web_app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="web_app/templates")

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Root route
@app.get("/")
async def root(request: Request):
    """Root page"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "German Apartment Finder"}
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "apartment-finder"}


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.web_host,
        port=settings.web_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
