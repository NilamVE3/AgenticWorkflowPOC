"""
Data schemas and models for the agent system
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"

class ToolParameter(BaseModel):
    """Schema for tool parameter definition"""
    name: str
    type: str
    description: str
    required: bool = False
    default: Any = None

class ToolInfo(BaseModel):
    """Schema for tool information"""
    name: str
    description: str
    parameters: Dict[str, ToolParameter]
    is_realtime: bool = False
    category: str = "general"

class ConnectionInfo(BaseModel):
    """Schema for connection information"""
    name: str
    type: str
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    last_activity: Optional[datetime] = None
    config: Dict[str, Any] = {}

class TaskRequest(BaseModel):
    """Schema for task execution request"""
    tool: str
    parameters: Dict[str, Any] = {}
    description: Optional[str] = None
    priority: str = "normal"
    timeout: Optional[int] = None

class TaskInfo(BaseModel):
    """Schema for task information"""
    task_id: str
    tool: str
    parameters: Dict[str, Any]
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    description: Optional[str] = None

class ExecutionHistory(BaseModel):
    """Schema for execution history"""
    tasks: List[TaskInfo] = []
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0

class AgentConfig(BaseModel):
    """Schema for agent configuration"""
    max_concurrent_tasks: int = 10
    default_timeout: int = 300
    enable_realtime_updates: bool = True
    log_level: str = "INFO"
    auto_register_tools: bool = True

class SystemStatus(BaseModel):
    """Schema for system status"""
    agent_status: str = "running"
    total_tools: int = 0
    active_connections: int = 0
    active_tasks: int = 0
    uptime: str
    memory_usage: Optional[Dict[str, Any]] = None

class APIResponse(BaseModel):
    """Schema for API responses"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class WebSocketMessage(BaseModel):
    """Schema for WebSocket messages"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    task_id: Optional[str] = None

class ToolExecutionRequest(BaseModel):
    """Schema for tool execution via WebSocket"""
    tool: str
    parameters: Dict[str, Any] = {}
    request_id: Optional[str] = None

class ToolExecutionResponse(BaseModel):
    """Schema for tool execution response"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tool: str
    request_id: Optional[str] = None
    execution_time: Optional[float] = None

class ConnectionAction(BaseModel):
    """Schema for connection actions"""
    connection: str
    action: str  # connect, disconnect, status
    parameters: Dict[str, Any] = {}

class ConnectionStatusUpdate(BaseModel):
    """Schema for connection status updates"""
    connection: str
    status: ConnectionStatus
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# Event schemas
class TaskUpdateEvent(BaseModel):
    """Schema for task update events"""
    task_id: str
    status: TaskStatus
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ToolProgressEvent(BaseModel):
    """Schema for tool progress events"""
    task_id: str
    tool: str
    message: str
    progress: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# Configuration schemas for specific integrations
class SlackConfig(BaseModel):
    """Slack integration configuration"""
    bot_token: str
    user_token: Optional[str] = None
    app_token: Optional[str] = None
    socket_mode_token: Optional[str] = None

class GmailConfig(BaseModel):
    """Gmail integration configuration"""
    client_id: str
    client_secret: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

class WeatherConfig(BaseModel):
    """Weather API configuration"""
    api_key: str
    default_location: Optional[str] = None
    units: str = "metric"

class DatabaseConfig(BaseModel):
    """Database configuration"""
    connection_string: str
    driver: str = "sqlite"
    pool_size: int = 5
    timeout: int = 30
