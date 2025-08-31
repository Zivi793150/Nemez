"""
Main API router
"""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.apartments import router as apartments_router
from app.api.filters import router as filters_router
from app.api.subscriptions import router as subscriptions_router
from app.api.notifications import router as notifications_router

# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(apartments_router, prefix="/apartments", tags=["Apartments"])
api_router.include_router(filters_router, prefix="/filters", tags=["Filters"])
api_router.include_router(subscriptions_router, prefix="/subscriptions", tags=["Subscriptions"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
