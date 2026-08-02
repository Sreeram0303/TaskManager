from fastapi import APIRouter, status, Request, Query
from src.task import controller
from src.task.dtos import TaskSchema, TaskUpdateSchema,TaskResponseSchema,TaskListResponseSchema
from fastapi import BackgroundTasks                      # ← with your other fastapi imports
from src.utils.activity import log_activity
from src.utils.dependencies import DbSession,CurrentUser

router = APIRouter(prefix="/tasks",tags=['Tasks'])

@router.post("", response_model=TaskResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_task(body: TaskSchema, background_tasks: BackgroundTasks,
                db: DbSession,request:Request,
                current_user: CurrentUser):
    redis_pool = request.app.state.redis_pool
    new_task = await controller.create_task(body, db, current_user.id,redis_pool)
    background_tasks.add_task(log_activity, current_user.id, "task_created", f"task {new_task.id}")
    return new_task


@router.get("",response_model=TaskListResponseSchema,responses={404:{"description":"Task not found"}},status_code=status.HTTP_200_OK)
async def get_all_tasks(request:Request,db:DbSession,current_user:CurrentUser,
                page:int = Query(1,ge=1),page_size:int = Query(20,ge=1,le=100),
                is_completed:bool|None = None,search:str|None = None):
    redis_pool = request.app.state.redis_pool
    return await controller.get_tasks(db,current_user.id,redis_pool,page,page_size,is_completed,search)

@router.get("/{task_id}",response_model=TaskResponseSchema,responses={404:{"description":"Task not found"}},status_code=status.HTTP_200_OK)
async def get_task(task_id:int,db:DbSession,current_user:CurrentUser):
    return await controller.get_task(task_id,db,current_user.id)

@router.patch("/{task_id}",response_model=TaskResponseSchema,responses={404:{"description":"Task not found"}},status_code=status.HTTP_200_OK)
async def modify_task(task_id:int,body:TaskUpdateSchema,
                background_tasks:BackgroundTasks,
                db:DbSession,request:Request,
                current_user:CurrentUser):
    redis_pool = request.app.state.redis_pool
    modified_task =  await controller.modify_task(task_id,body,db,current_user.id,redis_pool)
    background_tasks.add_task(log_activity,current_user.id,"task_modified",f"task {modified_task.id}")
    return modified_task

@router.put("/{task_id}",response_model=TaskResponseSchema,responses={404:{"description":"Task not found"}},status_code=status.HTTP_200_OK)
async def update_task(task_id:int,
                background_tasks:BackgroundTasks,
                body:TaskSchema,request:Request,
                db:DbSession,
                current_user:CurrentUser):
    redis_pool = request.app.state.redis_pool
    updated_task = await controller.update_task(task_id,body,db,current_user.id,redis_pool)
    background_tasks.add_task(log_activity,current_user.id,"task_updated",f"task {task_id}")
    return updated_task

@router.delete("/{task_id}",responses={404:{"description":"Task not found"}},status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id:int,
                 background_tasks:BackgroundTasks,
                db:DbSession,request:Request,
                current_user:CurrentUser):
    
    redis_pool = request.app.state.redis_pool
    await controller.delete_task(task_id,db,current_user.id,redis_pool)
    background_tasks.add_task(log_activity,current_user.id,"task_deleted",f"task {task_id}")
    return