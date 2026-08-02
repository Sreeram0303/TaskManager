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
        await redis_pool.publish(f"user:{user_id}:events",json.dumps({"event":"task_created","task":TaskResponseSchema.model_validate(new_task).model_dump(mode='json')}))
    except redis.exceptions.RedisError:
        # The write to Postgres already succeeded — a failed cache
        # invalidation shouldn't fail this request too. Worst case, the
        # list cache serves stale data until its TTL naturally expires.
        pass
    return new_task

async def get_tasks(db:AsyncSession,user_id:int,redis_pool:ArqRedis,page:int,page_size:int):
    # Cache key is unchanged from the pre-pagination design — still one
    # entry per user, holding the FULL task list. Given a personal task
    # list is realistically bounded (tens to low hundreds of rows, not
    # millions), it's cheaper to cache everything once and paginate in
    # memory than to hand-manage a separate cache key per page/page_size
    # combination — which would also mean every one of the 4 write paths
    # below would need to know how to find and clear an unknown SET of
    # keys instead of one hardcoded one.
    key = f"tasks:{user_id}"
    tasks = None
    try:
        cached_value = await redis_pool.get(key)
        if cached_value:
            tasks = json.loads(cached_value)
    except (redis.exceptions.RedisError, json.JSONDecodeError):
        # Redis unreachable, or the cached value was somehow malformed —
        # either way, treat it exactly like a normal cache miss and fall
        # through to the DB below, rather than failing the whole request.
        pass

    try:
        # "miss" covers every reason we're about to hit the DB — empty
        # cache, a Redis outage, or malformed JSON — not just "key absent".
        await redis_pool.incr("cache_stats:hits" if tasks is not None else "cache_stats:misses")
    except redis.exceptions.RedisError:
        pass

    if tasks is None:
        rows = (await db.scalars(select(Task).where(Task.user_id == user_id))).all()
        tasks = [TaskResponseSchema.model_validate(task).model_dump(mode='json') for task in rows]

        try:
            await redis_pool.set(key, json.dumps(tasks), ex=60)
        except redis.exceptions.RedisError:
            # We already have real data to return — a failed cache WRITE is a
            # missed optimization, not a reason to fail this request.
            pass

    start = (page - 1) * page_size
    end = start + page_size
    return {"items": tasks[start:end], "has_next": end < len(tasks)}

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
        await redis_pool.publish(f"user:{user_id}:events",json.dumps({"event":"task_updated","task":TaskResponseSchema.model_validate(task).model_dump(mode='json')}))
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
        await redis_pool.publish(f"user:{user_id}:events",json.dumps({"event":"task_updated","task":TaskResponseSchema.model_validate(task).model_dump(mode='json')}))
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
        await redis_pool.publish(f"user:{user_id}:events",json.dumps({"event":"task_deleted","task":TaskResponseSchema.model_validate(task).model_dump(mode='json')}))
    except redis.exceptions.RedisError:
        # The write to Postgres already succeeded — a failed cache
        # invalidation shouldn't fail this request too. Worst case, the
        # list cache serves stale data until its TTL naturally expires.
        pass
    return None