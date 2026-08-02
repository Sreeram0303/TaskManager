from fastapi import APIRouter, Depends, Request, status
from src.admin import controller
from src.admin.dtos import AdminDashboardSchema
from src.utils.dependencies import DbSession, require_permission

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/dashboard",
    response_model=AdminDashboardSchema,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("view_admin_dashboard"))],
)
async def get_dashboard(request: Request, db: DbSession):
    redis_pool = request.app.state.redis_pool
    return await controller.get_dashboard(db, redis_pool)
