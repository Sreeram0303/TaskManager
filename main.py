# from src.utils.db import Base,engine
# from src.task.models import Task
# from src.user.models import User
from fastapi import FastAPI
from src.task.router import router as task_router 
from src.user.router import router as user_router
from src.realtime.router import router as realtime_router
from src.metrics.router import router as metrics_router
from src.activity.router import router as activity_router
from contextlib import asynccontextmanager
from src.utils.logging import log_requests
from fastapi.middleware.cors import CORSMiddleware
from src.utils.arq_functions import REDIS_SETTINGS
from arq.connections import create_pool


# No need to create the tables at startup as alembic took the job of managing the db
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis_pool = await create_pool(REDIS_SETTINGS)
    yield
    await app.state.redis_pool.aclose()

app = FastAPI(lifespan=lifespan,title="Task Manager API", description="API for managing tasks", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500"],   # match your actual demo page's origin exactly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(log_requests)
app.include_router(task_router)
app.include_router(user_router)
app.include_router(realtime_router)
app.include_router(metrics_router)
app.include_router(activity_router)

