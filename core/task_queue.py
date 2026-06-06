"""
core/task_queue.py — asyncio 기반 작업 큐

동시 실행을 제한하고 작업 상태를 추적하는 태스크 큐.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Any

logger = logging.getLogger(__name__)


@dataclass
class Task:
    name: str
    coro_fn: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "pending"   # pending | running | done | failed
    result: Any = None
    error: str = ""


class TaskQueue:
    def __init__(self, max_concurrent: int = 3):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._tasks: list[Task] = []
        self._running = False

    def enqueue(self, name: str, coro_fn: Callable, *args, **kwargs) -> Task:
        task = Task(name=name, coro_fn=coro_fn, args=args, kwargs=kwargs)
        self._tasks.append(task)
        self._queue.put_nowait(task)
        logger.debug(f"[TaskQueue] 작업 추가: {name}")
        return task

    async def start(self):
        self._running = True
        logger.info("[TaskQueue] 시작")
        while self._running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                asyncio.create_task(self._run(task))
            except asyncio.TimeoutError:
                continue

    async def _run(self, task: Task):
        async with self._semaphore:
            task.status = "running"
            logger.info(f"[TaskQueue] 실행: {task.name}")
            try:
                task.result = await task.coro_fn(*task.args, **task.kwargs)
                task.status = "done"
                logger.info(f"[TaskQueue] 완료: {task.name}")
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                logger.error(f"[TaskQueue] 실패: {task.name} — {e}")
            finally:
                self._queue.task_done()

    def stop(self):
        self._running = False

    def get_stats(self) -> dict:
        counts = {"pending": 0, "running": 0, "done": 0, "failed": 0}
        for t in self._tasks:
            counts[t.status] = counts.get(t.status, 0) + 1
        return counts
