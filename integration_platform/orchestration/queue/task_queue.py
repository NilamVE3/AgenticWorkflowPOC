"""
Task Queue System - Durable execution with queues and workers
"""

from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import json
import uuid
import logging
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

class QueueType(str, Enum):
    DEFAULT = "default"
    HIGH_PRIORITY = "high_priority"
    WORKFLOW = "workflow"
    WEBHOOK = "webhook"
    SCHEDULED = "scheduled"

@dataclass
class RetryPolicy:
    """Retry policy for tasks"""
    max_attempts: int = 3
    backoff_type: str = "exponential"  # linear, exponential, fixed
    backoff_interval: int = 1  # seconds
    max_backoff_interval: int = 300  # seconds
    jitter: bool = True  # Add randomness to prevent thundering herd

class TaskDefinition(BaseModel):
    """Definition of a task"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str
    payload: Dict[str, Any] = {}
    priority: TaskPriority = TaskPriority.NORMAL
    queue: QueueType = QueueType.DEFAULT
    retry_policy: Optional[RetryPolicy] = None
    timeout: Optional[int] = 300  # seconds
    delay_until: Optional[datetime] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None

class TaskExecution(BaseModel):
    """Execution record for a task"""
    task_id: str
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    attempt: int = 1
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = {}

class TaskQueue:
    """In-memory task queue with persistence support"""
    
    def __init__(self, queue_type: QueueType):
        self.queue_type = queue_type
        self._tasks: Dict[str, TaskDefinition] = {}
        self._executions: Dict[str, TaskExecution] = {}
        self._priority_queue = asyncio.PriorityQueue()
        self._delayed_tasks: List[TaskDefinition] = []
        self._lock = asyncio.Lock()
    
    async def enqueue(self, task: TaskDefinition) -> str:
        """
        Add a task to the queue
        
        Args:
            task: Task definition
            
        Returns:
            Task ID
        """
        async with self._lock:
            task.queue = self.queue_type
            self._tasks[task.task_id] = task
            
            # Create execution record
            execution = TaskExecution(task_id=task.task_id)
            self._executions[task.task_id] = execution
            
            # Add to appropriate queue
            if task.delay_until and task.delay_until > datetime.now():
                self._delayed_tasks.append(task)
            else:
                await self._priority_queue.put((
                    self._get_priority_value(task.priority),
                    task.task_id
                ))
            
            logger.info(f"Enqueued task {task.task_id} to {self.queue_type}")
            return task.task_id
    
    async def dequeue(self, timeout: float = 1.0) -> Optional[TaskDefinition]:
        """
        Get next task from queue
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Task definition or None
        """
        # Check for delayed tasks
        await self._process_delayed_tasks()
        
        try:
            _, task_id = await asyncio.wait_for(
                self._priority_queue.get(),
                timeout=timeout
            )
            return self._tasks.get(task_id)
        except asyncio.TimeoutError:
            return None
    
    async def get_task(self, task_id: str) -> Optional[TaskDefinition]:
        """Get task by ID"""
        return self._tasks.get(task_id)
    
    async def get_execution(self, task_id: str) -> Optional[TaskExecution]:
        """Get execution record by task ID"""
        return self._executions.get(task_id)
    
    async def update_execution(self, task_id: str, updates: Dict[str, Any]):
        """Update execution record"""
        if task_id in self._executions:
            execution = self._executions[task_id]
            for key, value in updates.items():
                if hasattr(execution, key):
                    setattr(execution, key, value)
    
    async def retry_task(self, task_id: str, delay: float = 0):
        """Retry a failed task"""
        task = self._tasks.get(task_id)
        execution = self._executions.get(task_id)
        
        if not task or not execution:
            return
        
        # Update execution
        execution.attempt += 1
        execution.status = TaskStatus.RETRYING
        
        # Update task delay
        if delay > 0:
            task.delay_until = datetime.now() + timedelta(seconds=delay)
            self._delayed_tasks.append(task)
        else:
            await self._priority_queue.put((
                self._get_priority_value(task.priority),
                task_id
            ))
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        if task_id in self._executions:
            self._executions[task_id].status = TaskStatus.CANCELLED
            return True
        return False
    
    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> List[TaskDefinition]:
        """List tasks with optional status filter"""
        tasks = list(self._tasks.values())
        
        if status:
            task_ids = [
                task_id for task_id, exec in self._executions.items()
                if exec.status == status
            ]
            tasks = [t for t in tasks if t.task_id in task_ids]
        
        return tasks[:limit]
    
    async def _process_delayed_tasks(self):
        """Process delayed tasks that are ready"""
        now = datetime.now()
        ready_tasks = []
        
        for task in self._delayed_tasks:
            if task.delay_until and task.delay_until <= now:
                ready_tasks.append(task)
        
        for task in ready_tasks:
            self._delayed_tasks.remove(task)
            await self._priority_queue.put((
                self._get_priority_value(task.priority),
                task.task_id
            ))
    
    def _get_priority_value(self, priority: TaskPriority) -> int:
        """Convert priority to numeric value for queue"""
        priority_map = {
            TaskPriority.URGENT: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.NORMAL: 2,
            TaskPriority.LOW: 3
        }
        return priority_map.get(priority, 2)

class WorkerPool:
    """Pool of worker processes"""
    
    def __init__(self, num_workers: int = 10):
        self.num_workers = num_workers
        self._workers: List[Worker] = []
        self._running = False
        self._task_handlers: Dict[str, Callable] = {}
    
    def register_handler(self, task_type: str, handler: Callable):
        """Register a task handler"""
        self._task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")
    
    async def start(self, queues: List[TaskQueue]):
        """Start the worker pool"""
        self._running = True
        
        # Create workers
        for i in range(self.num_workers):
            worker = Worker(f"worker-{i}", self._task_handlers, queues)
            self._workers.append(worker)
            asyncio.create_task(worker.run())
        
        logger.info(f"Started {self.num_workers} workers")
    
    async def stop(self):
        """Stop the worker pool"""
        self._running = False
        
        # Stop all workers
        for worker in self._workers:
            await worker.stop()
        
        logger.info("Stopped worker pool")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker pool statistics"""
        return {
            "total_workers": self.num_workers,
            "active_workers": len([w for w in self._workers if w.is_running]),
            "registered_handlers": list(self._task_handlers.keys()),
            "worker_stats": [w.get_stats() for w in self._workers]
        }

class Worker:
    """Individual worker process"""
    
    def __init__(
        self,
        worker_id: str,
        task_handlers: Dict[str, Callable],
        queues: List[TaskQueue]
    ):
        self.worker_id = worker_id
        self.task_handlers = task_handlers
        self.queues = queues
        self.is_running = False
        self.current_task: Optional[str] = None
        self.stats = {
            "tasks_processed": 0,
            "tasks_failed": 0,
            "total_execution_time": 0.0,
            "last_activity": None
        }
    
    async def run(self):
        """Main worker loop"""
        self.is_running = True
        logger.info(f"Worker {self.worker_id} started")
        
        while self.is_running:
            task = await self._get_next_task()
            
            if task:
                await self._process_task(task)
            else:
                # No task available, brief pause
                await asyncio.sleep(0.1)
        
        logger.info(f"Worker {self.worker_id} stopped")
    
    async def _get_next_task(self) -> Optional[TaskDefinition]:
        """Get next task from any queue"""
        # Try queues in priority order
        queue_priority = [
            QueueType.HIGH_PRIORITY,
            QueueType.WORKFLOW,
            QueueType.WEBHOOK,
            QueueType.DEFAULT,
            QueueType.SCHEDULED
        ]
        
        for queue_type in queue_priority:
            queue = next((q for q in self.queues if q.queue_type == queue_type), None)
            if queue:
                task = await queue.dequeue(timeout=0.1)
                if task:
                    return task
        
        return None
    
    async def _process_task(self, task: TaskDefinition):
        """Process a single task"""
        self.current_task = task.task_id
        start_time = datetime.now()
        
        try:
            # Update execution status
            await self._update_task_status(task.task_id, TaskStatus.RUNNING, self.worker_id)
            
            # Get handler
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"No handler for task type: {task.task_type}")
            
            # Execute task with timeout
            timeout = task.timeout or 300
            result = await asyncio.wait_for(
                handler(task.payload),
                timeout=timeout
            )
            
            # Update execution with success
            execution_time = (datetime.now() - start_time).total_seconds()
            await self._update_task_status(
                task.task_id,
                TaskStatus.COMPLETED,
                result=result,
                execution_time=execution_time
            )
            
            self.stats["tasks_processed"] += 1
            self.stats["total_execution_time"] += execution_time
            
        except asyncio.TimeoutError:
            error = f"Task timeout after {task.timeout or 300} seconds"
            await self._handle_task_failure(task, error, start_time)
        
        except Exception as e:
            await self._handle_task_failure(task, str(e), start_time)
        
        finally:
            self.current_task = None
            self.stats["last_activity"] = datetime.now().isoformat()
    
    async def _handle_task_failure(self, task: TaskDefinition, error: str, start_time: datetime):
        """Handle task failure with retry logic"""
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Check if we should retry
        if task.retry_policy:
            queue = next((q for q in self.queues if q.queue_type == task.queue), None)
            if queue:
                execution = await queue.get_execution(task.task_id)
                
                if execution and execution.attempt < task.retry_policy.max_attempts:
                    # Calculate retry delay
                    delay = self._calculate_retry_delay(execution.attempt, task.retry_policy)
                    
                    # Retry the task
                    await queue.retry_task(task.task_id, delay)
                    await self._update_task_status(
                        task.task_id,
                        TaskStatus.RETRYING,
                        error=error,
                        execution_time=execution_time
                    )
                    
                    logger.warning(f"Task {task.task_id} will retry in {delay}s (attempt {execution.attempt})")
                    return
        
        # No more retries, mark as failed
        await self._update_task_status(
            task.task_id,
            TaskStatus.FAILED,
            error=error,
            execution_time=execution_time
        )
        
        self.stats["tasks_failed"] += 1
        logger.error(f"Task {task.task_id} failed permanently: {error}")
    
    async def _update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        worker_id: str = None,
        result: Dict[str, Any] = None,
        error: str = None,
        execution_time: float = None
    ):
        """Update task execution status"""
        # Find the queue containing this task
        for queue in self.queues:
            execution = await queue.get_execution(task_id)
            if execution:
                updates = {"status": status}
                
                if worker_id:
                    updates["worker_id"] = worker_id
                if result:
                    updates["result"] = result
                if error:
                    updates["error"] = error
                if execution_time is not None:
                    updates["execution_time"] = execution_time
                
                if status == TaskStatus.RUNNING:
                    updates["started_at"] = datetime.now()
                elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    updates["completed_at"] = datetime.now()
                
                await queue.update_execution(task_id, updates)
                break
    
    def _calculate_retry_delay(self, attempt: int, policy: RetryPolicy) -> float:
        """Calculate retry delay based on policy"""
        if policy.backoff_type == "linear":
            delay = policy.backoff_interval * attempt
        elif policy.backoff_type == "exponential":
            delay = policy.backoff_interval * (2 ** (attempt - 1))
        else:  # fixed
            delay = policy.backoff_interval
        
        # Apply maximum limit
        delay = min(delay, policy.max_backoff_interval)
        
        # Add jitter if enabled
        if policy.jitter:
            import random
            jitter_factor = 0.8 + (random.random() * 0.4)  # 80% to 120%
            delay *= jitter_factor
        
        return delay
    
    async def stop(self):
        """Stop the worker"""
        self.is_running = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        return {
            "worker_id": self.worker_id,
            "is_running": self.is_running,
            "current_task": self.current_task,
            **self.stats
        }

class OrchestrationManager:
    """Main orchestration manager"""
    
    def __init__(self):
        self.queues: Dict[QueueType, TaskQueue] = {}
        self.worker_pool: Optional[WorkerPool] = None
        self._running = False
    
    def initialize(self, num_workers: int = 10):
        """Initialize the orchestration system"""
        # Create queues
        for queue_type in QueueType:
            self.queues[queue_type] = TaskQueue(queue_type)
        
        # Create worker pool
        self.worker_pool = WorkerPool(num_workers)
        
        logger.info("Orchestration manager initialized")
    
    async def start(self):
        """Start the orchestration system"""
        if not self.worker_pool:
            raise RuntimeError("Orchestration manager not initialized")
        
        await self.worker_pool.start(list(self.queues.values()))
        self._running = True
        
        logger.info("Orchestration system started")
    
    async def stop(self):
        """Stop the orchestration system"""
        if self.worker_pool:
            await self.worker_pool.stop()
        
        self._running = False
        logger.info("Orchestration system stopped")
    
    async def enqueue_task(self, task: TaskDefinition) -> str:
        """Enqueue a task"""
        queue = self.queues.get(task.queue, self.queues[QueueType.DEFAULT])
        return await queue.enqueue(task)
    
    async def get_task_status(self, task_id: str) -> Optional[TaskExecution]:
        """Get task execution status"""
        for queue in self.queues.values():
            execution = await queue.get_execution(task_id)
            if execution:
                return execution
        return None
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """Register a task handler"""
        if self.worker_pool:
            self.worker_pool.register_handler(task_type, handler)
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        stats = {
            "running": self._running,
            "queues": {},
            "worker_pool": {}
        }
        
        # Queue stats
        for queue_type, queue in self.queues.items():
            stats["queues"][queue_type.value] = {
                "total_tasks": len(queue._tasks),
                "pending_tasks": len([t for t in queue._tasks.values() 
                                   if queue._executions[t.task_id].status == TaskStatus.PENDING]),
                "running_tasks": len([t for t in queue._tasks.values() 
                                    if queue._executions[t.task_id].status == TaskStatus.RUNNING]),
                "delayed_tasks": len(queue._delayed_tasks)
            }
        
        # Worker pool stats
        if self.worker_pool:
            stats["worker_pool"] = self.worker_pool.get_stats()
        
        return stats

# Global orchestration manager
orchestration_manager = OrchestrationManager()
