from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ActivityLogResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id : int
    action : str
    detail : str | None
    created_at : datetime


class ActivityListResponseSchema(BaseModel):
    items : list[ActivityLogResponseSchema]
    has_next : bool
