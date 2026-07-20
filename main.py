# from src.utils.db import Base,engine
# from src.task.models import Task
# from src.user.models import User
from fastapi import FastAPI
from src.task.router import router as task_router 
from src.user.router import router as user_router
from contextlib import asynccontextmanager

# No need to create the tables at startup as alembic took the job of managing the db
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     Base.metadata.create_all(bind=engine)
#     yield
app = FastAPI(title="Task Manager API", description="API for managing tasks", version="1.0.0")

app.include_router(task_router)
app.include_router(user_router)

