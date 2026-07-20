from pydantic import BaseModel,ConfigDict,Field
from datetime import datetime

# title max_length mirrors the column: models.py Task.title = String(100).
# Keeping the Pydantic edge constraint in sync with the DB constraint means
# an over-long title is rejected with a 422 here, not a DB-level error.
class TaskSchema(BaseModel):
    title : str = Field(min_length=1,max_length=100)
    description : str | None = Field(default=None,max_length=2000)
    # description is optional here to match the model (Mapped[str | None])
    # and TaskResponseSchema below — previously required=str here promised
    # a description that could never actually be null end-to-end.

class TaskUpdateSchema(BaseModel):
    title : str | None = Field(default=None,min_length=1,max_length=100)
    description : str | None = Field(default=None,max_length=2000)
    is_completed : bool | None = None

class TaskResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id : int
    title : str
    description : str | None
    is_completed : bool
    created_at : datetime