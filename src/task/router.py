from fastapi import APIRouter,Depends, status
from src.task import controller
from src.task.dtos import TaskSchema, TaskUpdateSchema,TaskResponseSchema
from src.utils.db import get_db
from sqlalchemy.orm import Session
from src.user.models import User
from src.utils.dependencies import get_current_user
from fastapi import BackgroundTasks                      # ← with your other fastapi imports
from src.utils.activity import log_activity

router = APIRouter(prefix="/tasks",tags=['Tasks'])
@router.post("", response_model=TaskResponseSchema, status_code=status.HTTP_201_CREATED)
def create_task(body: TaskSchema, background_tasks: BackgroundTasks,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    new_task = controller.create_task(body, db, current_user.id)
    background_tasks.add_task(log_activity, current_user.id, "task_created", f"task {new_task.id}")
    return new_task


@router.get("",response_model=list[TaskResponseSchema],responses={404:{"description":"Task not found"}},status_code=status.HTTP_200_OK)
def get_all_tasks(db:Session=Depends(get_db),current_user:User =Depends(get_current_user)):
    return controller.get_tasks(db,current_user.id)

@router.get("/{task_id}",response_model=TaskResponseSchema,responses={404:{"description":"Task not found"}},status_code=status.HTTP_200_OK)
def get_task(task_id:int,db:Session=Depends(get_db),current_user:User =Depends(get_current_user)):
    return controller.get_task(task_id,db,current_user.id)

@router.patch("/{task_id}",response_model=TaskResponseSchema,responses={404:{"description":"Task not found"}},status_code=status.HTTP_200_OK)
def modify_task(task_id:int,body:TaskUpdateSchema,
                background_tasks:BackgroundTasks,
                db:Session=Depends(get_db),
                current_user:User =Depends(get_current_user)):
    modified_task =  controller.modify_task(task_id,body,db,current_user.id)
    background_tasks.add_task(log_activity,current_user.id,"task_modified",f"task {modified_task.id}")
    return modified_task

@router.put("/{task_id}",response_model=TaskResponseSchema,responses={404:{"description":"Task not found"}},status_code=status.HTTP_200_OK)
def update_task(task_id:int,
                background_tasks:BackgroundTasks,
                body:TaskSchema,
                db:Session=Depends(get_db),
                current_user:User =Depends(get_current_user)):
    updated_task = controller.update_task(task_id,body,db,current_user.id)
    background_tasks.add_task(log_activity,current_user.id,"task_updated",f"task {task_id}")
    return updated_task

@router.delete("/{task_id}",responses={404:{"description":"Task not found"}},status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id:int,
                 background_tasks:BackgroundTasks,
                db:Session=Depends(get_db),
                current_user:User =Depends(get_current_user)):
    
    controller.delete_task(task_id,db,current_user.id)
    background_tasks.add_task(log_activity,current_user.id,"task_deleted",f"task {task_id}")
    return