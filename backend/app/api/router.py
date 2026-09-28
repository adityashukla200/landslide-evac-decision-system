"""Main API v1 router mounting all sub-routers."""

from fastapi import APIRouter
from backend.app.api.endpoints.data import router as data_router
from backend.app.api.endpoints.thresholds import router as thresholds_router
from backend.app.api.endpoints.evacuation import router as evacuation_router
from backend.app.api.endpoints.alerting import router as alerting_router
from backend.app.api.endpoints.replay import router as replay_router
from backend.app.api.endpoints.sensors import router as sensors_router
from backend.app.api.endpoints.security import router as security_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(data_router)
api_router.include_router(thresholds_router)
api_router.include_router(evacuation_router)
api_router.include_router(alerting_router)
api_router.include_router(replay_router)
api_router.include_router(sensors_router)
api_router.include_router(security_router)
