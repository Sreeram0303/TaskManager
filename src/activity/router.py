from fastapi import APIRouter, Query, status
from src.activity import controller
from src.activity.dtos import ActivityListResponseSchema
from src.utils.dependencies import DbSession, CurrentUser

router = APIRouter(prefix="/activity", tags=["Activity"])


@router.get("", response_model=ActivityListResponseSchema, status_code=status.HTTP_200_OK)
async def get_activity(db: DbSession, current_user: CurrentUser,
                page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    return await controller.get_activity(db, current_user.id, page, page_size)
