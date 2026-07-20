from src.task.dtos import TaskSchema, TaskUpdateSchema
from src.task.models import Task
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException


def get_task_or_404(db:Session,task_id:int,user_id:int):
    task = db.get(Task,task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404,detail = f"Task {task_id} not found")
    return task

def create_task(body : TaskSchema,db:Session,user_id:int):
    new_task = Task(**body.model_dump(),user_id = user_id)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

def get_tasks(db:Session,user_id:int):
    tasks = db.scalars(select(Task).where(Task.user_id == user_id)).all()
    return tasks

def get_task(task_id:int,db:Session,user_id:int):
    return get_task_or_404(db,task_id,user_id)

def modify_task(task_id:int,body:TaskUpdateSchema,db:Session,user_id:int):
    task = get_task_or_404(db,task_id,user_id)
    
    for field,value in body.model_dump(exclude_unset=True).items():
        setattr(task,field,value)
        
    db.commit()
    db.refresh(task)
    return task

def update_task(task_id:int,body:TaskSchema,db:Session,user_id:int):
    task = get_task_or_404(db,task_id,user_id)
    
    for field,value in body.model_dump().items():
        setattr(task,field,value)
        
    db.commit()
    db.refresh(task)
    return task

def delete_task(task_id:int,db:Session,user_id:int):
    task = get_task_or_404(db,task_id,user_id)
    db.delete(task)
    db.commit()
    return None