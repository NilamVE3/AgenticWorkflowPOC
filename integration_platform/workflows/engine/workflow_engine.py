"""
Workflow Engine - JSON DAG execution engine
"""

from typing import Dict, Any, List, Optional, Union, Set
from datetime import datetime, timedelta
from enum import Enum
import json
import asyncio
import uuid
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class StepType(str, Enum):
    ACTION = "action"
    TRIGGER = "trigger"
    CONDITION = "condition"
    PARALLEL = "parallel"
    DELAY = "delay"
    WEBHOOK = "webhook"
    LOOP = "loop"

class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

class RetryPolicy(BaseModel):
    """Retry policy for workflow steps"""
    max_attempts: int = 3
    backoff_type: str = "exponential"  # linear, exponential, fixed
    backoff_interval: int = 1  # seconds
    max_backoff_interval: int = 300  # seconds

class WorkflowStep(BaseModel):
    """Definition of a workflow step"""
    id: str
    name: str
    description: Optional[str] = None
    type: StepType
    config: Dict[str, Any] = {}
    depends_on: List[str] = []  # Step IDs this step depends on
    retry_policy: Optional[RetryPolicy] = None
    timeout: Optional[int] = 300  # seconds
    condition: Optional[str] = None  # Conditional execution
    parallel_branches: Optional[List[Dict[str, Any]]] = None  # For parallel steps

class WorkflowDefinition(BaseModel):
    """Definition of a workflow"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    trigger: Dict[str, Any] = {}  # Workflow trigger configuration
    steps: List[WorkflowStep] = []
    variables: Dict[str, Any] = {}  # Global variables
    settings: Dict[str, Any] = {}  # Workflow settings
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[str] = None
    tags: List[str] = []

class WorkflowExecution(BaseModel):
    """Execution instance of a workflow"""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.ACTIVE
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    trigger_data: Dict[str, Any] = {}
    context: Dict[str, Any] = {}  # Execution context
    step_executions: Dict[str, Dict[str, Any]] = {}  # Step execution data
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}

class StepExecution(BaseModel):
    """Execution data for a single step"""
    step_id: str
    execution_id: str
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input_data: Dict[str, Any] = {}
    output_data: Dict[str, Any] = {}
    error: Optional[str] = None
    attempt: int = 1
    metadata: Dict[str, Any] = {}

class WorkflowEngine:
    """Main workflow execution engine"""
    
    def __init__(self, tool_executor, trigger_system):
        self.tool_executor = tool_executor
        self.trigger_system = trigger_system
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._executions: Dict[str, WorkflowExecution] = {}
        self._step_executions: Dict[str, StepExecution] = {}
        self._running_executions: Dict[str, asyncio.Task] = {}
    
    def register_workflow(self, workflow_def: WorkflowDefinition) -> str:
        """
        Register a new workflow
        
        Args:
            workflow_def: Workflow definition
            
        Returns:
            Workflow ID
        """
        # Validate workflow
        self._validate_workflow(workflow_def)
        
        # Store workflow
        self._workflows[workflow_def.id] = workflow_def
        
        # Register trigger if needed
        if workflow_def.trigger:
            self.trigger_system.register_workflow_trigger(
                workflow_def.id,
                workflow_def.trigger
            )
        
        logger.info(f"Registered workflow: {workflow_def.name} ({workflow_def.id})")
        return workflow_def.id
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get workflow by ID"""
        return self._workflows.get(workflow_id)
    
    def list_workflows(self, status: Optional[WorkflowStatus] = None) -> List[WorkflowDefinition]:
        """List workflows with optional status filter"""
        workflows = list(self._workflows.values())
        
        if status:
            # Filter by checking if there are active executions
            active_workflow_ids = {
                exec.workflow_id for exec in self._executions.values()
                if exec.status == status
            }
            workflows = [w for w in workflows if w.id in active_workflow_ids]
        
        return workflows
    
    async def execute_workflow(
        self,
        workflow_id: str,
        trigger_data: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """
        Execute a workflow
        
        Args:
            workflow_id: Workflow ID
            trigger_data: Data that triggered the workflow
            context: Execution context
            
        Returns:
            Execution ID
        """
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        # Create execution instance
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            trigger_data=trigger_data or {},
            context=context or {}
        )
        
        self._executions[execution.execution_id] = execution
        
        # Start execution in background
        task = asyncio.create_task(
            self._execute_workflow_async(execution.execution_id)
        )
        self._running_executions[execution.execution_id] = task
        
        logger.info(f"Started workflow execution: {execution.execution_id}")
        return execution.execution_id
    
    async def _execute_workflow_async(self, execution_id: str):
        """Async workflow execution"""
        execution = self._executions.get(execution_id)
        if not execution:
            return
        
        workflow = self._workflows.get(execution.workflow_id)
        if not workflow:
            execution.status = WorkflowStatus.FAILED
            execution.error = "Workflow not found"
            return
        
        try:
            # Initialize execution context
            context = {
                "trigger_data": execution.trigger_data,
                "workflow_variables": workflow.variables,
                "user_context": execution.context,
                "step_results": {}
            }
            
            # Create step execution records
            for step in workflow.steps:
                step_exec = StepExecution(
                    step_id=step.id,
                    execution_id=execution_id
                )
                self._step_executions[f"{execution_id}:{step.id}"] = step_exec
                execution.step_executions[step.id] = step_exec.dict()
            
            # Build dependency graph
            dependency_graph = self._build_dependency_graph(workflow.steps)
            
            # Execute steps in order
            await self._execute_steps(execution_id, workflow.steps, dependency_graph, context)
            
            # Mark execution as completed
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.now()
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.now()
        
        finally:
            # Clean up running execution
            if execution_id in self._running_executions:
                del self._running_executions[execution_id]
    
    def _build_dependency_graph(self, steps: List[WorkflowStep]) -> Dict[str, Set[str]]:
        """Build dependency graph from steps"""
        graph = {}
        for step in steps:
            graph[step.id] = set(step.depends_on)
        return graph
    
    async def _execute_steps(
        self,
        execution_id: str,
        steps: List[WorkflowStep],
        dependency_graph: Dict[str, Set[str]],
        context: Dict[str, Any]
    ):
        """Execute steps respecting dependencies"""
        completed_steps = set()
        failed_steps = set()
        
        while len(completed_steps) < len(steps) and not failed_steps:
            # Find steps ready to execute
            ready_steps = []
            for step in steps:
                if (step.id not in completed_steps and 
                    step.id not in failed_steps and
                    dependency_graph[step.id].issubset(completed_steps)):
                    ready_steps.append(step)
            
            if not ready_steps:
                if failed_steps:
                    break
                # No steps ready but not completed - circular dependency
                raise ValueError("Circular dependency detected in workflow")
            
            # Execute ready steps (can be parallel)
            tasks = []
            for step in ready_steps:
                task = asyncio.create_task(
                    self._execute_step(execution_id, step, context)
                )
                tasks.append((step.id, task))
            
            # Wait for all ready steps to complete
            for step_id, task in tasks:
                try:
                    success = await task
                    if success:
                        completed_steps.add(step_id)
                    else:
                        failed_steps.add(step_id)
                except Exception as e:
                    logger.error(f"Step {step_id} failed: {str(e)}")
                    failed_steps.add(step_id)
        
        if failed_steps:
            raise RuntimeError(f"Workflow failed: {len(failed_steps)} steps failed")
    
    async def _execute_step(
        self,
        execution_id: str,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> bool:
        """Execute a single step"""
        step_exec_key = f"{execution_id}:{step.id}"
        step_exec = self._step_executions.get(step_exec_key)
        
        if not step_exec:
            return False
        
        step_exec.status = StepStatus.RUNNING
        step_exec.started_at = datetime.now()
        
        try:
            # Check condition if present
            if step.condition and not self._evaluate_condition(step.condition, context):
                step_exec.status = StepStatus.SKIPPED
                step_exec.completed_at = datetime.now()
                return True
            
            # Execute based on step type
            if step.type == StepType.ACTION:
                result = await self._execute_action_step(step, context)
            elif step.type == StepType.CONDITION:
                result = await self._execute_condition_step(step, context)
            elif step.type == StepType.PARALLEL:
                result = await self._execute_parallel_step(step, context)
            elif step.type == StepType.DELAY:
                result = await self._execute_delay_step(step, context)
            elif step.type == StepType.WEBHOOK:
                result = await self._execute_webhook_step(step, context)
            elif step.type == StepType.LOOP:
                result = await self._execute_loop_step(step, context)
            else:
                raise ValueError(f"Unknown step type: {step.type}")
            
            # Store result
            step_exec.output_data = result
            step_exec.status = StepStatus.COMPLETED
            step_exec.completed_at = datetime.now()
            
            # Update context
            context["step_results"][step.id] = result
            
            return True
            
        except Exception as e:
            logger.error(f"Step {step.id} execution failed: {str(e)}")
            step_exec.error = str(e)
            step_exec.status = StepStatus.FAILED
            step_exec.completed_at = datetime.now()
            
            # Handle retries
            if step.retry_policy and step_exec.attempt < step.retry_policy.max_attempts:
                return await self._retry_step(execution_id, step, context)
            
            return False
    
    async def _execute_action_step(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action step"""
        tool_id = step.config.get("tool_id")
        if not tool_id:
            raise ValueError("Action step requires tool_id")
        
        # Prepare parameters with variable substitution
        parameters = self._substitute_variables(step.config.get("parameters", {}), context)
        
        # Create execution request
        from tools.registry.tool_registry import ToolExecutionRequest
        request = ToolExecutionRequest(
            tool_id=tool_id,
            parameters=parameters,
            user_context=context.get("user_context", {})
        )
        
        # Execute tool
        result = await self.tool_executor.execute(request)
        
        if not result.success:
            raise RuntimeError(result.error or "Tool execution failed")
        
        return result.result or {}
    
    async def _execute_condition_step(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a condition step"""
        condition = step.config.get("condition")
        if not condition:
            raise ValueError("Condition step requires condition")
        
        result = self._evaluate_condition(condition, context)
        return {"condition_result": result}
    
    async def _execute_parallel_step(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute parallel branches"""
        branches = step.config.get("branches", [])
        if not branches:
            raise ValueError("Parallel step requires branches")
        
        tasks = []
        for branch in branches:
            task = asyncio.create_task(
                self._execute_branch(branch, context)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "branch_results": [
                result if not isinstance(result, Exception) else {"error": str(result)}
                for result in results
            ]
        }
    
    async def _execute_delay_step(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a delay step"""
        delay_seconds = step.config.get("delay_seconds", 1)
        await asyncio.sleep(delay_seconds)
        return {"delayed": True, "seconds": delay_seconds}
    
    async def _execute_webhook_step(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a webhook step"""
        url = step.config.get("url")
        if not url:
            raise ValueError("Webhook step requires url")
        
        # Substitute variables in URL and payload
        url = self._substitute_variables(url, context)
        payload = self._substitute_variables(step.config.get("payload", {}), context)
        
        # Make webhook call
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                return {"webhook_result": result}
    
    async def _execute_loop_step(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a loop step"""
        loop_config = step.config.get("loop", {})
        loop_type = loop_config.get("type", "fixed")
        
        if loop_type == "fixed":
            iterations = loop_config.get("iterations", 1)
            results = []
            for i in range(iterations):
                # Update context with iteration
                context["loop_iteration"] = i
                result = await self._execute_loop_body(step, context)
                results.append(result)
            
            return {"loop_results": results}
        
        else:
            raise ValueError(f"Unknown loop type: {loop_type}")
    
    async def _execute_loop_body(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute loop body steps"""
        body_steps = step.config.get("body", [])
        results = {}
        
        for body_step_config in body_steps:
            # Create temporary step
            body_step = WorkflowStep(**body_step_config)
            result = await self._execute_step("temp", body_step, context)
            results[body_step.id] = result
        
        return results
    
    async def _execute_branch(self, branch: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a parallel branch"""
        branch_steps = [WorkflowStep(**step_config) for step_config in branch.get("steps", [])]
        
        # Execute branch steps
        branch_context = context.copy()
        for step in branch_steps:
            await self._execute_step("temp", step, branch_context)
        
        return branch_context.get("step_results", {})
    
    async def _retry_step(self, execution_id: str, step: WorkflowStep, context: Dict[str, Any]) -> bool:
        """Retry a failed step"""
        step_exec_key = f"{execution_id}:{step.id}"
        step_exec = self._step_executions.get(step_exec_key)
        
        if not step_exec or not step.retry_policy:
            return False
        
        # Calculate backoff delay
        delay = self._calculate_backoff_delay(step_exec.attempt, step.retry_policy)
        await asyncio.sleep(delay)
        
        # Increment attempt and retry
        step_exec.attempt += 1
        step_exec.status = StepStatus.PENDING
        
        return await self._execute_step(execution_id, step, context)
    
    def _calculate_backoff_delay(self, attempt: int, policy: RetryPolicy) -> float:
        """Calculate retry backoff delay"""
        if policy.backoff_type == "linear":
            return policy.backoff_interval * attempt
        elif policy.backoff_type == "exponential":
            delay = policy.backoff_interval * (2 ** (attempt - 1))
            return min(delay, policy.max_backoff_interval)
        else:  # fixed
            return policy.backoff_interval
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition expression"""
        # Simple condition evaluation - in production, use a proper expression parser
        try:
            # Replace variables in condition
            for key, value in context.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        condition = condition.replace(f"{{{key}.{sub_key}}}", str(sub_value))
                else:
                    condition = condition.replace(f"{{{key}}}", str(value))
            
            # Evaluate the condition (simplified)
            return bool(eval(condition))
        except:
            return False
    
    def _substitute_variables(self, data: Any, context: Dict[str, Any]) -> Any:
        """Substitute variables in data"""
        if isinstance(data, str):
            # Replace {{variable}} syntax
            import re
            pattern = r'\{\{([^}]+)\}\}'
            
            def replace_var(match):
                var_path = match.group(1).strip()
                return self._get_nested_value(var_path, context, "")
            
            return re.sub(pattern, replace_var, data)
        elif isinstance(data, dict):
            return {k: self._substitute_variables(v, context) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_variables(item, context) for item in data]
        else:
            return data
    
    def _get_nested_value(self, path: str, data: Dict[str, Any], default: Any) -> Any:
        """Get nested value from dictionary using dot notation"""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def _validate_workflow(self, workflow: WorkflowDefinition):
        """Validate workflow definition"""
        if not workflow.name:
            raise ValueError("Workflow name is required")
        
        # Check for duplicate step IDs
        step_ids = [step.id for step in workflow.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Duplicate step IDs found")
        
        # Check dependencies
        defined_steps = set(step_ids)
        for step in workflow.steps:
            for dep in step.depends_on:
                if dep not in defined_steps:
                    raise ValueError(f"Step {step.id} depends on undefined step {dep}")
    
    def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get execution status"""
        return self._executions.get(execution_id)
    
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution"""
        execution = self._executions.get(execution_id)
        if not execution:
            return False
        
        if execution_id in self._running_executions:
            task = self._running_executions[execution_id]
            task.cancel()
            del self._running_executions[execution_id]
        
        execution.status = WorkflowStatus.CANCELLED
        execution.completed_at = datetime.now()
        
        return True

# Global workflow engine instance
workflow_engine = WorkflowEngine(
    tool_executor=None,  # Will be set during initialization
    trigger_system=None   # Will be set during initialization
)
