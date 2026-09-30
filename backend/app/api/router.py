"""Main API v1 router mounting all sub-routers."""

from fastapi import APIRouter
from backend.app.api.endpoints.data import router as data_router
from backend.app.api.endpoints.thresholds import router as thresholds_router
from backend.app.api.endpoints.evacuation import router as evacuation_router
from backend.app.api.endpoints.alerting import router as alerting_router
from backend.app.api.endpoints.replay import router as replay_router
from backend.app.api.endpoints.sensors import router as sensors_router
from backend.app.api.endpoints.security import router as security_router
from backend.app.api.endpoints.citizen_reports import router as citizen_reports_router
from backend.app.api.endpoints.ai_cv import router as ai_cv_router
from backend.app.api.endpoints.satellite import router as satellite_router
from backend.app.api.endpoints.mesh import router as mesh_router
from backend.app.api.endpoints.dynamic_routing import router as dynamic_routing_router
from backend.app.api.endpoints.telecom import router as telecom_router
from backend.app.api.endpoints.institutional import router as institutional_router
from backend.app.api.endpoints.copilot import router as copilot_router
from backend.app.api.endpoints.auth import router as auth_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(data_router)
api_router.include_router(thresholds_router)
api_router.include_router(evacuation_router)
api_router.include_router(citizen_reports_router)
api_router.include_router(ai_cv_router)
api_router.include_router(satellite_router)
api_router.include_router(mesh_router)
api_router.include_router(dynamic_routing_router)
api_router.include_router(telecom_router)
api_router.include_router(institutional_router)
api_router.include_router(copilot_router)




api_router.include_router(alerting_router)
api_router.include_router(replay_router)
api_router.include_router(sensors_router)
api_router.include_router(security_router)


