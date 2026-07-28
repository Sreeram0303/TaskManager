from src.task.dtos import TaskSchema, TaskUpdateSchema
from src.task.models import Task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException


async def get_task_or_404(db:AsyncSession,task_id:int,user_id:int):
    task = await db.get(Task,task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404,detail = f"Task {task_id} not found")
    return task

async def create_task(body : TaskSchema,db:AsyncSession,user_id:int):
    new_task = Task(**body.model_dump(),user_id = user_id)
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task

async def get_tasks(db:AsyncSession,user_id:int):
    tasks =(await db.scalars(select(Task).where(Task.user_id == user_id))).all()
    return tasks

async def get_task(task_id:int,db:AsyncSession,user_id:int):
    return await get_task_or_404(db,task_id,user_id)

async def modify_task(task_id:int,body:TaskUpdateSchema,db:AsyncSession,user_id:int):
    task = await get_task_or_404(db,task_id,user_id)
    
    for field,value in body.model_dump(exclude_unset=True).items():
        setattr(task,field,value)
        
    await db.commit()
    await db.refresh(task)
    return task

async def update_task(task_id:int,body:TaskSchema,db:AsyncSession,user_id:int):
    task = await get_task_or_404(db,task_id,user_id)
    
    for field,value in body.model_dump().items():
        setattr(task,field,value)
        
    await db.commit()
    await db.refresh(task)
    return task

async def delete_task(task_id:int,db:AsyncSession,user_id:int):
    task = await get_task_or_404(db,task_id,user_id)
    await db.delete(task)
    await db.commit()
    return None