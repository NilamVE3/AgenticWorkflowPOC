"""
Tool Registry - Central registry for all tools/actions
"""

from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
from enum import Enum
import json
import logging
import asyncio
import uuid
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ToolStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    ERROR = "error"

class ToolCategory(str, Enum):
    COMMUNICATION = "communication"
    DATA_MANAGEMENT = "data_management"
    AUTOMATION = "automation"
    ANALYTICS = "analytics"
    DEVELOPMENT = "development"
    MARKETING = "marketing"
    SALES = "sales"
    HR = "hr"
    FINANCE = "finance"
    GENERAL = "general"

class ToolParameter(BaseModel):
    """Schema for tool parameter"""
    name: str
    type: str  # string, integer, number, boolean, array, object
    description: str
    required: bool = False
    default: Any = None
    enum: Optional[List[Any]] = None
    format: Optional[str] = None  # email, date-time, uri, etc.
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    min_items: Optional[int] = None
    max_items: Optional[int] = None

class ToolDefinition(BaseModel):
    """Definition of a tool/action"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    category: ToolCategory = ToolCategory.GENERAL
    connector_name: str
    connector_action: str
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}
    parameters: List[ToolParameter] = []
    rate_limit: Dict[str, Any] = {}
    tags: List[str] = []
    version: str = "1.0.0"
    status: ToolStatus = ToolStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ToolExecutionRequest(BaseModel):
    """Request for tool execution"""
    tool_id: str
    parameters: Dict[str, Any] = {}
    user_context: Dict[str, Any] = {}
    execution_id: Optional[str] = None
    timeout: Optional[int] = 300
    priority: str = "normal"  # low, normal, high, urgent

class ToolExecutionResult(BaseModel):
    """Result of tool execution"""
    success: bool
    tool_id: str
    execution_id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = {}

class ToolRegistry:
    """Central registry for managing tools"""
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._tool_index: Dict[str, str] = {}  # name/alias -> id
        self._category_index: Dict[ToolCategory, List[str]] = {}
        self._connector_index: Dict[str, List[str]] = {}
        self._execution_stats: Dict[str, Dict[str, Any]] = {}
    
    def register_tool(self, tool_def: ToolDefinition) -> str:
        """
        Register a new tool
        
        Args:
            tool_def: Tool definition
            
        Returns:
            Tool ID
        """
        # Validate tool definition
        self._validate_tool(tool_def)
        
        # Store tool
        self._tools[tool_def.id] = tool_def
        
        # Update indexes
        self._tool_index[tool_def.name] = tool_def.id
        for tag in tool_def.tags:
            self._tool_index[tag] = tool_def.id
        
        # Category index
        if tool_def.category not in self._category_index:
            self._category_index[tool_def.category] = []
        self._category_index[tool_def.category].append(tool_def.id)
        
        # Connector index
        if tool_def.connector_name not in self._connector_index:
            self._connector_index[tool_def.connector_name] = []
        self._connector_index[tool_def.connector_name].append(tool_def.id)
        
        # Initialize execution stats
        self._execution_stats[tool_def.id] = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "last_execution": None
        }
        
        logger.info(f"Registered tool: {tool_def.name} ({tool_def.id})")
        return tool_def.id
    
    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """Get tool by ID"""
        return self._tools.get(tool_id)
    
    def get_tool_by_name(self, name: str) -> Optional[ToolDefinition]:
        """Get tool by name or alias"""
        tool_id = self._tool_index.get(name)
        return self._tools.get(tool_id) if tool_id else None
    
    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        connector: Optional[str] = None,
        status: Optional[ToolStatus] = None,
        tags: Optional[List[str]] = None
    ) -> List[ToolDefinition]:
        """
        List tools with optional filters
        
        Args:
            category: Filter by category
            connector: Filter by connector
            status: Filter by status
            tags: Filter by tags
            
        Returns:
            List of tools
        """
        tools = list(self._tools.values())
        
        if category:
            tool_ids = self._category_index.get(category, [])
            tools = [t for t in tools if t.id in tool_ids]
        
        if connector:
            tool_ids = self._connector_index.get(connector, [])
            tools = [t for t in tools if t.id in tool_ids]
        
        if status:
            tools = [t for t in tools if t.status == status]
        
        if tags:
            tools = [t for t in tools if any(tag in t.tags for tag in tags)]
        
        return tools
    
    def search_tools(self, query: str) -> List[ToolDefinition]:
        """
        Search tools by name, description, or tags
        
        Args:
            query: Search query
            
        Returns:
            List of matching tools
        """
        query = query.lower()
        results = []
        
        for tool in self._tools.values():
            if (query in tool.name.lower() or 
                query in tool.description.lower() or
                any(query in tag.lower() for tag in tool.tags)):
                results.append(tool)
        
        return results
    
    def update_tool(self, tool_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update tool definition
        
        Args:
            tool_id: Tool ID
            updates: Updates to apply
            
        Returns:
            True if update successful
        """
        if tool_id not in self._tools:
            return False
        
        tool = self._tools[tool_id]
        
        # Update fields
        for key, value in updates.items():
            if hasattr(tool, key):
                setattr(tool, key, value)
        
        tool.updated_at = datetime.now()
        logger.info(f"Updated tool: {tool.name} ({tool_id})")
        return True
    
    def deactivate_tool(self, tool_id: str) -> bool:
        """Deactivate a tool"""
        return self.update_tool(tool_id, {"status": ToolStatus.INACTIVE})
    
    def get_tool_stats(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get execution statistics for a tool"""
        return self._execution_stats.get(tool_id)
    
    def update_execution_stats(
        self,
        tool_id: str,
        success: bool,
        execution_time: float
    ):
        """Update execution statistics for a tool"""
        if tool_id not in self._execution_stats:
            return
        
        stats = self._execution_stats[tool_id]
        stats["total_executions"] += 1
        stats["last_execution"] = datetime.now().isoformat()
        
        if success:
            stats["successful_executions"] += 1
        else:
            stats["failed_executions"] += 1
        
        # Update average execution time
        total = stats["total_executions"]
        current_avg = stats["average_execution_time"]
        stats["average_execution_time"] = (
            (current_avg * (total - 1) + execution_time) / total
        )
    
    def _validate_tool(self, tool: ToolDefinition):
        """Validate tool definition"""
        if not tool.name:
            raise ValueError("Tool name is required")
        
        if not tool.description:
            raise ValueError("Tool description is required")
        
        if not tool.connector_name:
            raise ValueError("Connector name is required")
        
        if not tool.connector_action:
            raise ValueError("Connector action is required")
        
        # Validate JSON schemas
        if tool.input_schema:
            try:
                json.dumps(tool.input_schema)
            except TypeError as e:
                raise ValueError(f"Invalid input schema: {e}")
        
        if tool.output_schema:
            try:
                json.dumps(tool.output_schema)
            except TypeError as e:
                raise ValueError(f"Invalid output schema: {e}")

class ToolExecutor:
    """Tool execution engine"""
    
    def __init__(self, tool_registry: ToolRegistry, connector_registry):
        self.registry = tool_registry
        self.connector_registry = connector_registry
        self._active_executions: Dict[str, asyncio.Task] = {}
    
    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """
        Execute a tool
        
        Args:
            request: Tool execution request
            
        Returns:
            Execution result
        """
        execution_id = request.execution_id or str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            # Get tool definition
            tool = self.registry.get_tool(request.tool_id)
            if not tool:
                return ToolExecutionResult(
                    success=False,
                    tool_id=request.tool_id,
                    execution_id=execution_id,
                    error=f"Tool {request.tool_id} not found",
                    execution_time=0.0
                )
            
            # Validate tool status
            if tool.status != ToolStatus.ACTIVE:
                return ToolExecutionResult(
                    success=False,
                    tool_id=request.tool_id,
                    execution_id=execution_id,
                    error=f"Tool {tool.name} is {tool.status.value}",
                    execution_time=0.0
                )
            
            # Validate parameters
            validation_result = self._validate_parameters(tool, request.parameters)
            if not validation_result.valid:
                return ToolExecutionResult(
                    success=False,
                    tool_id=request.tool_id,
                    execution_id=execution_id,
                    error=f"Parameter validation failed: {validation_result.error}",
                    execution_time=0.0
                )
            
            # Get connector instance
            connector_instance = self._get_connector_instance(
                tool.connector_name,
                request.user_context
            )
            
            if not connector_instance:
                return ToolExecutionResult(
                    success=False,
                    tool_id=request.tool_id,
                    execution_id=execution_id,
                    error=f"Connector {tool.connector_name} not available",
                    execution_time=0.0
                )
            
            # Execute the action
            result = await self._execute_with_timeout(
                connector_instance,
                tool.connector_action,
                request.parameters,
                request.user_context,
                request.timeout
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Update stats
            self.registry.update_execution_stats(
                request.tool_id,
                result.get("success", False),
                execution_time
            )
            
            return ToolExecutionResult(
                success=result.get("success", False),
                tool_id=request.tool_id,
                execution_id=execution_id,
                result=result.get("data") if result.get("success") else None,
                error=result.get("error") if not result.get("success") else None,
                execution_time=execution_time,
                metadata=result.get("metadata", {})
            )
            
        except asyncio.TimeoutError:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.registry.update_execution_stats(request.tool_id, False, execution_time)
            
            return ToolExecutionResult(
                success=False,
                tool_id=request.tool_id,
                execution_id=execution_id,
                error="Execution timeout",
                execution_time=execution_time
            )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.registry.update_execution_stats(request.tool_id, False, execution_time)
            logger.error(f"Tool execution failed: {str(e)}")
            
            return ToolExecutionResult(
                success=False,
                tool_id=request.tool_id,
                execution_id=execution_id,
                error=str(e),
                execution_time=execution_time
            )
    
    def _validate_parameters(self, tool: ToolDefinition, parameters: Dict[str, Any]) -> Any:
        """Validate parameters against tool schema"""
        # Simple validation - in production, use jsonschema
        for param in tool.parameters:
            if param.required and param.name not in parameters:
                return type('ValidationResult', (), {
                    'valid': False,
                    'error': f'Required parameter {param.name} missing'
                })()
        
        return type('ValidationResult', (), {'valid': True})()
    
    def _get_connector_instance(self, connector_name: str, user_context: Dict[str, Any]):
        """Get connector instance for user"""
        # In production, this would get user-specific connector instance
        # For now, create a temporary instance
        try:
            connector_class = self.connector_registry._connector_classes.get(connector_name)
            if connector_class:
                return connector_class()
        except Exception as e:
            logger.error(f"Failed to get connector instance: {str(e)}")
        
        return None
    
    async def _execute_with_timeout(
        self,
        connector,
        action: str,
        parameters: Dict[str, Any],
        user_context: Dict[str, Any],
        timeout: int
    ) -> Dict[str, Any]:
        """Execute connector action with timeout"""
        try:
            return await asyncio.wait_for(
                connector.execute_action(action, parameters, user_context),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            return {"success": False, "error": str(e)}

# Global tool registry
tool_registry = ToolRegistry()
