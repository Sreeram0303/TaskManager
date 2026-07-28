from src.task.dtos import TaskSchema, TaskUpdateSchema, TaskResponseSchema
from src.task.models import Task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from arq.connections import ArqRedis
import redis.exceptions
import json
async def get_task_or_404(db:AsyncSession,task_id:int,user_id:int):
    task = await db.get(Task,task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404,detail = f"Task {task_id} not found")
    return task

async def create_task(body : TaskSchema,db:AsyncSession,user_id:int,redis_pool:ArqRedis):
    new_task = Task(**body.model_dump(),user_id = user_id)
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    key = f"tasks:{user_id}"
    try:
        await redis_pool.delete(key)
    except redis.exceptions.RedisError:
        # The write to Postgres already succeeded — a failed cache
        # invalidation shouldn't fail this request too. Worst case, the
        # list cache serves stale data until its TTL naturally expires.
        pass
    return new_task

async def get_tasks(db:AsyncSession,user_id:int,redis_pool:ArqRedis):
    key = f"tasks:{user_id}"
    try:
        cached_value = await redis_pool.get(key)
        if cached_value:
            return json.loads(cached_value)
    except (redis.exceptions.RedisError, json.JSONDecodeError):
        # Redis unreachable, or the cached value was somehow malformed —
        # either way, treat it exactly like a normal cache miss and fall
        # through to the DB below, rather than failing the whole request.
        pass

    tasks = (await db.scalars(select(Task).where(Task.user_id == user_id))).all()
    redis_list = []
    for task in tasks:
        redis_list.append(TaskResponseSchema.model_validate(task).model_dump(mode='json'))

    try:
        await redis_pool.set(key, json.dumps(redis_list), ex=60)
    except redis.exceptions.RedisError:
        # We already have real data to return — a failed cache WRITE is a
        # missed optimization, not a reason to fail this request.
        pass

    return tasks

async def get_task(task_id:int,db:AsyncSession,user_id:int):
    return await get_task_or_404(db,task_id,user_id)

async def modify_task(task_id:int,body:TaskUpdateSchema,db:AsyncSession,user_id:int,redis_pool:ArqRedis):
    task = await get_task_or_404(db,task_id,user_id)
    
    for field,value in body.model_dump(exclude_unset=True).items():
        setattr(task,field,value)
        
    await db.commit()
    await db.refresh(task)
    
    key = f"tasks:{user_id}"
    try:
        await redis_pool.delete(key)
    except redis.exceptions.RedisError:
        # The write to Postgres already succeeded — a failed cache
        # invalidation shouldn't fail this request too. Worst case, the
        # list cache serves stale data until its TTL naturally expires.
        pass
    return task

async def update_task(task_id:int,body:TaskSchema,db:AsyncSession,user_id:int,redis_pool:ArqRedis):
    task = await get_task_or_404(db,task_id,user_id)
    
    for field,value in body.model_dump().items():
        setattr(task,field,value)
        
    await db.commit()
    await db.refresh(task)
    
    key = f"tasks:{user_id}"
    try:
        await redis_pool.delete(key)
    except redis.exceptions.RedisError:
        # The write to Postgres already succeeded — a failed cache
        # invalidation shouldn't fail this request too. Worst case, the
        # list cache serves stale data until its TTL naturally expires.
        pass
    return task

async def delete_task(task_id:int,db:AsyncSession,user_id:int,redis_pool:ArqRedis):
    task = await get_task_or_404(db,task_id,user_id)
    await db.delete(task)
    await db.commit()
    key = f"tasks:{user_id}"
    try:
        await redis_pool.delete(key)
    except redis.exceptions.RedisError:
        # The write to Postgres already succeeded — a failed cache
        # invalidation shouldn't fail this request too. Worst case, the
        # list cache serves stale data until its TTL naturally expires.
        pass
    return None