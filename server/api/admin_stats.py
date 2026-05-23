from core.dependencies import is_admin
from db import get_db
from fastapi import APIRouter, Depends
from services.admin_stats_service import AdminStatsService
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.admin_stats import AdminStatsResponse
from schemas.profile_stats import ProfileStatsResponse
from services.progress_service import ProgressService

router = APIRouter(prefix="/admin/stats", tags=["admin-stats"])
async def get_progress_service(db: AsyncSession = Depends(get_db)) -> ProgressService:
    return ProgressService(db)

async def get_admin_stats_service(
    db: AsyncSession = Depends(get_db),
) -> AdminStatsService:
    return AdminStatsService(db)


@router.get("/dashboard", response_model=AdminStatsResponse)
async def get_admin_dashboard_stats(
    period_days: int = 30,
    current_admin=Depends(is_admin),
    stats_service: AdminStatsService = Depends(get_admin_stats_service),
):
    return await stats_service.get_dashboard_stats(period_days)


@router.get("/user/{user_id}/stats", response_model=ProfileStatsResponse)
async def get_user_stats(
    user_id: int,
    current_admin = Depends(is_admin),
    progress_service: ProgressService = Depends(get_progress_service)
):
    return await progress_service.get_profile_stats(user_id=user_id)