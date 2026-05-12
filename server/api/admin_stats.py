from core.dependencies import is_admin
from db import get_db
from fastapi import APIRouter, Depends
from services.admin_stats_service import AdminStatsService
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.admin_stats import AdminStatsResponse

router = APIRouter(prefix="/admin/stats", tags=["admin-stats"])


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
