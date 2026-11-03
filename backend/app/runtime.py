"""Cancellation must join filesystem writers before a scan can be deleted."""
import asyncio

async def blocking(func, *args, **kwargs):
    task = asyncio.create_task(asyncio.to_thread(func, *args, **kwargs))
    cancelled = False
    while True:
        try:
            result = await asyncio.shield(task)
            break
        except asyncio.CancelledError:
            cancelled = True
            if task.done():
                task.result()
                break
    if cancelled:
        raise asyncio.CancelledError
    return result

async def together(*coroutines):
    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(c) for c in coroutines]
    return [t.result() for t in tasks]
