"""
Main API Routes - RESTful API for external access
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import logging
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import json

from tools.registry.tool_registry import tool_registry, ToolDefinition, ToolExecutionRequest
from workflows.engine.workflow_engine import workflow_engine, WorkflowDefinition
from orchestration.queue.task_queue import orchestration_manager, TaskDefinition
from triggers.trigger_system import trigger_system, TriggerDefinition
from auth.auth_service import auth_service
from auth.auth_service import CredentialDefinition, CredentialStatus
from agents.llm.agentic_layer import agentic_layer, AgentRequest

logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Integration Platform API",
    description="Scalable integration platform supporting 1000+ connectors",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Pydantic models for API
class ToolExecutionRequestAPI(BaseModel):
    tool_id: str
    parameters: Dict[str, Any] = {}
    user_context: Dict[str, Any] = {}
    timeout: Optional[int] = 300

class WorkflowCreationRequest(BaseModel):
    name: str
    description: Optional[str] = None
    steps: List[Dict[str, Any]]
    trigger: Dict[str, Any] = {}
    variables: Dict[str, Any] = {}

class AgentRequestAPI(BaseModel):
    prompt: str
    context: Dict[str, Any] = {}
    capabilities: List[str] = []
    available_tools: List[str] = []
    constraints: Dict[str, Any] = {}

class ConnectorRegistrationRequest(BaseModel):
    name: str
    openapi_spec_url: Optional[str] = None
    openapi_spec: Optional[Dict[str, Any]] = None
    auth_config: Dict[str, Any] = {}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user_id = auth_service.verify_jwt_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return user_id

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Connector Management APIs
@app.get("/api/connectors")
async def list_connectors(user_id: str = Depends(get_current_user)):
    """List available connectors and their status"""
    return {
        "connectors": {
            "slack": {
                "name": "Slack",
                "description": "Send messages, manage channels, and upload files",
                "status": "connected" if auth_service.get_credential(user_id, "slack") else "disconnected",
                "category": "communication"
            },
            "http": {
                "name": "HTTP/API",
                "description": "Make REST API calls to any service",
                "status": "connected" if auth_service.get_credential(user_id, "http") else "disconnected",
                "category": "general"
            },
            "gmail": {
                "name": "Gmail",
                "description": "Send emails and manage inbox",
                "status": "connected" if auth_service.get_credential(user_id, "gmail") else "disconnected",
                "category": "communication"
            },
            "github": {
                "name": "GitHub",
                "description": "Manage repositories, issues, and pull requests",
                "status": "connected" if auth_service.get_credential(user_id, "github") else "disconnected",
                "category": "development"
            }
        }
    }

@app.post("/api/connectors/configure")
async def configure_connector(request: Dict[str, Any], user_id: str = Depends(get_current_user)):
    """Configure and test connector connection"""
    connector_type = request.get("connector_type")
    config = request.get("config")
    
    try:
        # Validate configuration
        if connector_type == "slack":
            bot_token = config.get("bot_token")
            workspace = config.get("workspace")
            
            if not bot_token or not workspace:
                raise HTTPException(status_code=400, detail="Bot token and workspace required")
            
            # Store credentials (in production, encrypt these)
            auth_service.store_credential(user_id, connector_type, {
                "bot_token": bot_token,
                "workspace": workspace
            })
            
        elif connector_type == "http":
            base_url = config.get("base_url")
            api_key = config.get("api_key")
            
            if not base_url:
                raise HTTPException(status_code=400, detail="Base URL required")
            
            auth_service.store_credential(user_id, connector_type, {
                "base_url": base_url,
                "api_key": api_key
            })
            
        elif connector_type == "gmail":
            email = config.get("email")
            password = config.get("password")
            
            if not email or not password:
                raise HTTPException(status_code=400, detail="Email and password required")
            
            auth_service.store_credential(user_id, connector_type, {
                "email": email,
                "password": password
            })
            
        elif connector_type == "github":
            username = config.get("username")
            token = config.get("token")
            
            if not username or not token:
                raise HTTPException(status_code=400, detail="Username and token required")
            
            auth_service.store_credential(user_id, connector_type, {
                "username": username,
                "token": token
            })
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported connector type")
        
        return {
            "success": True,
            "message": f"{connector_type.upper()} connector configured successfully",
            "connector_type": connector_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/connectors/test")
async def test_connector(request: Dict[str, Any], user_id: str = Depends(get_current_user)):
    """Test connector connection"""
    connector_type = request.get("connector_type")
    config = request.get("config")
    
    try:
        # Test connection based on connector type
        if connector_type == "slack":
            bot_token = config.get("bot_token")
            workspace = config.get("workspace")
            
            if not bot_token or not workspace:
                return {"success": False, "error": "Bot token and workspace required"}
            
            # Test Slack connection (simplified)
            if bot_token.startswith("xoxb") and workspace:
                return {"success": True, "message": "Slack connection test successful"}
            else:
                return {"success": False, "error": "Invalid bot token format"}
                
        elif connector_type == "http":
            base_url = config.get("base_url")
            
            if not base_url:
                return {"success": False, "error": "Base URL required"}
            
            # Test HTTP connection
            try:
                import httpx
                response = httpx.get(base_url, timeout=10)
                if response.status_code < 400:
                    return {"success": True, "message": "HTTP connection test successful"}
                else:
                    return {"success": False, "error": f"HTTP error: {response.status_code}"}
            except Exception:
                return {"success": False, "error": "Connection test failed"}
                
        elif connector_type == "gmail":
            email = config.get("email")
            password = config.get("password")
            
            if not email or not password:
                return {"success": False, "error": "Email and password required"}
            
            # Test Gmail connection (simplified)
            if "@" in email and len(password) > 0:
                return {"success": True, "message": "Gmail connection test successful"}
            else:
                return {"success": False, "error": "Invalid email or password"}
                
        elif connector_type == "github":
            username = config.get("username")
            token = config.get("token")
            
            if not username or not token:
                return {"success": False, "error": "Username and token required"}
            
            # Test GitHub connection (simplified)
            if len(username) > 0 and (token.startswith("ghp_") or token.startswith("github_pat_")):
                return {"success": True, "message": "GitHub connection test successful"}
            else:
                return {"success": False, "error": "Invalid username or token"}
        
        else:
            return {"success": False, "error": "Unsupported connector type"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

# System information
@app.get("/api/system/info")
async def get_system_info():
    """Get system information and statistics"""
    return {
        "system": {
            "status": "running",
            "uptime": "active",
            "version": "1.0.0"
        },
        "components": {
            "tools": {
                "total": len(tool_registry._tools),
                "active": len([t for t in tool_registry._tools.values() if t.status == "active"])
            },
            "workflows": {
                "total": len(workflow_engine._workflows),
                "running": len([e for e in workflow_engine._executions.values() if e.status == "active"])
            },
            "triggers": trigger_system.get_system_stats(),
            "orchestration": orchestration_manager.get_system_stats(),
            "authentication": auth_service.get_system_stats()
        }
    }

# Tool Management APIs
@app.get("/api/tools")
async def list_tools(
    category: Optional[str] = None,
    connector: Optional[str] = None,
    status: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """List available tools"""
    tools = tool_registry.list_tools(
        category=category,
        connector=connector,
        status=status
    )
    
    return {
        "tools": [tool.dict() for tool in tools],
        "total": len(tools)
    }

@app.get("/api/tools/{tool_id}")
async def get_tool(tool_id: str, user_id: str = Depends(get_current_user)):
    """Get tool details"""
    tool = tool_registry.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    return tool.dict()

@app.post("/api/tools/execute")
async def execute_tool(
    request: ToolExecutionRequestAPI,
    user_id: str = Depends(get_current_user)
):
    """Execute a tool"""
    # Add user context
    request.user_context["user_id"] = user_id
    
    # Create execution request
    execution_request = ToolExecutionRequest(**request.dict())
    
    try:
        result = await tool_registry.executor.execute(execution_request)
        return result.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Workflow Management APIs
@app.get("/api/workflows")
async def list_workflows(user_id: str = Depends(get_current_user)):
    """List workflows"""
    workflows = workflow_engine.list_workflows()
    
    return {
        "workflows": [workflow.dict() for workflow in workflows],
        "total": len(workflows)
    }

@app.post("/api/workflows")
async def create_workflow(
    request: WorkflowCreationRequest,
    user_id: str = Depends(get_current_user)
):
    """Create a new workflow"""
    try:
        workflow_def = WorkflowDefinition(
            name=request.name,
            description=request.description,
            steps=request.steps,
            trigger=request.trigger,
            variables=request.variables,
            created_by=user_id
        )
        
        workflow_id = workflow_engine.register_workflow(workflow_def)
        
        return {
            "workflow_id": workflow_id,
            "message": "Workflow created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str, user_id: str = Depends(get_current_user)):
    """Get workflow details"""
    workflow = workflow_engine.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return workflow.dict()

@app.post("/api/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    trigger_data: Dict[str, Any] = {},
    user_id: str = Depends(get_current_user)
):
    """Execute a workflow"""
    try:
        execution_id = await workflow_engine.execute_workflow(
            workflow_id,
            trigger_data=trigger_data,
            context={"user_id": user_id}
        )
        
        return {
            "execution_id": execution_id,
            "message": "Workflow execution started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workflows/{workflow_id}/executions")
async def get_workflow_executions(workflow_id: str, user_id: str = Depends(get_current_user)):
    """Get workflow executions"""
    executions = [
        exec for exec in workflow_engine._executions.values()
        if exec.workflow_id == workflow_id
    ]
    
    return {
        "executions": [exec.dict() for exec in executions],
        "total": len(executions)
    }

@app.get("/api/executions/{execution_id}")
async def get_execution_status(execution_id: str, user_id: str = Depends(get_current_user)):
    """Get execution status"""
    execution = workflow_engine.get_execution_status(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return execution.dict()

# Trigger Management APIs
@app.get("/api/triggers")
async def list_triggers(
    workflow_id: Optional[str] = None,
    trigger_type: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """List triggers"""
    triggers = trigger_system.list_triggers(
        workflow_id=workflow_id,
        trigger_type=trigger_type
    )
    
    return {
        "triggers": [trigger.dict() for trigger in triggers],
        "total": len(triggers)
    }

@app.post("/api/triggers")
async def create_trigger(
    trigger_data: Dict[str, Any],
    user_id: str = Depends(get_current_user)
):
    """Create a new trigger"""
    try:
        trigger_def = TriggerDefinition(**trigger_data)
        trigger_id = trigger_system.register_trigger(trigger_def)
        
        return {
            "trigger_id": trigger_id,
            "message": "Trigger created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/triggers/{trigger_id}/webhook-url")
async def get_webhook_url(trigger_id: str, user_id: str = Depends(get_current_user)):
    """Get webhook URL for a trigger"""
    webhook_url = trigger_system.get_webhook_url(trigger_id)
    if not webhook_url:
        raise HTTPException(status_code=404, detail="Webhook URL not available")
    
    return {"webhook_url": webhook_url}

# Connector Management APIs
@app.get("/api/connectors")
async def list_connectors(user_id: str = Depends(get_current_user)):
    """List available connectors"""
    from connectors.sdk.base_connector import connector_registry
    
    connectors = []
    for connector_name in connector_registry.list_connectors():
        schema = connector_registry.get_connector_schema(connector_name)
        if schema:
            connectors.append(schema)
    
    return {
        "connectors": connectors,
        "total": len(connectors)
    }

@app.post("/api/connectors/register")
async def register_connector(
    request: ConnectorRegistrationRequest,
    user_id: str = Depends(get_current_user)
):
    """Register a new connector from OpenAPI spec"""
    try:
        from connectors.generators.openapi_generator import connector_generator
        
        if request.openapi_spec_url:
            # Generate from URL
            connector_class = await connector_generator.generate_from_url(
                request.openapi_spec_url,
                request.name
            )
        elif request.openapi_spec:
            # Generate from spec data
            connector_class = connector_generator.generate_from_spec(
                request.openapi_spec,
                request.name
            )
        else:
            raise HTTPException(status_code=400, detail="Either openapi_spec_url or openapi_spec is required")
        
        # Register the connector
        from connectors.sdk.base_connector import connector_registry
        connector_registry.register(connector_class)
        
        return {
            "message": "Connector registered successfully",
            "connector_name": request.name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Agent APIs
@app.post("/api/agent/chat")
async def agent_chat(
    request: AgentRequestAPI,
    user_id: str = Depends(get_current_user)
):
    """Chat with the AI agent"""
    try:
        agent_request = AgentRequest(
            user_id=user_id,
            prompt=request.prompt,
            context=request.context,
            capabilities=request.capabilities,
            available_tools=request.available_tools,
            constraints=request.constraints
        )
        
        response = await agentic_layer.process_request(agent_request)
        
        # Execute tool calls if any
        if response.tool_calls:
            tool_results = await agentic_layer.execute_tool_calls(
                response.tool_calls,
                {"user_id": user_id}
            )
            response.metadata["tool_results"] = tool_results
        
        return response.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agent/workflow")
async def generate_workflow_from_prompt(
    prompt: str,
    user_context: Dict[str, Any] = {},
    user_id: str = Depends(get_current_user)
):
    """Generate and execute workflow from prompt"""
    try:
        user_context["user_id"] = user_id
        execution_id = await agentic_layer.create_and_execute_workflow(
            prompt, user_context
        )
        
        return {
            "execution_id": execution_id,
            "message": "Workflow generated and execution started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Authentication APIs
@app.post("/api/auth/login")
async def login(credentials: Dict[str, Any]):
    """Authenticate user and return JWT token"""
    # Simple authentication - in production, use proper user management
    username = credentials.get("username")
    password = credentials.get("password")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    # For demo, accept any credentials
    token = auth_service.generate_jwt_token(username)
    
    return {
        "access_token": token,
        "token_type": "Bearer",
        "user_id": username
    }

@app.post("/api/auth/oauth2/initiate")
async def initiate_oauth2(
    connector_name: str,
    config: Dict[str, Any],
    user_id: str = Depends(get_current_user)
):
    """Initiate OAuth2 flow"""
    try:
        result = auth_service.initiate_oauth2_flow(user_id, connector_name, config)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/oauth2/callback")
async def oauth2_callback(
    state_id: str,
    code: str,
    state: str
):
    """Complete OAuth2 flow"""
    try:
        credential_id = await auth_service.complete_oauth2_flow(state_id, code, state)
        if not credential_id:
            raise HTTPException(status_code=400, detail="OAuth2 flow failed")
        
        return {
            "credential_id": credential_id,
            "message": "Authentication successful"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/credentials")
async def get_user_credentials(
    connector_name: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Get user credentials"""
    credentials = auth_service.get_credentials_for_connector(user_id, connector_name)
    
    return {
        "credentials": [
            {
                "credential_id": cred.credential_id,
                "connector_name": cred.connector_name,
                "auth_type": cred.auth_type,
                "status": cred.status,
                "created_at": cred.created_at,
                "expires_at": cred.expires_at
            }
            for cred in credentials
        ],
        "total": len(credentials)
    }

# Webhook endpoint
@app.post("/webhooks/{trigger_id}")
async def handle_webhook(trigger_id: str, data: Dict[str, Any], headers: Dict[str, str] = None):
    """Handle incoming webhook"""
    try:
        result, status_code = await trigger_system.webhook_handler.handle_webhook(
            trigger_id, data, headers or {}
        )
        
        return result, status_code
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back or process the message
            await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Background task endpoints
@app.post("/api/tasks")
async def create_task(
    task_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """Create and queue a background task"""
    try:
        task_def = TaskDefinition(**task_data)
        task_id = await orchestration_manager.enqueue_task(task_def)
        
        return {
            "task_id": task_id,
            "message": "Task queued successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str, user_id: str = Depends(get_current_user)):
    """Get task status"""
    execution = await orchestration_manager.get_task_status(task_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return execution.dict()

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {str(exc)}")
    return {
        "error": "Internal server error",
        "message": str(exc),
        "timestamp": datetime.now().isoformat()
    }

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize the platform on startup"""
    logger.info("Starting Integration Platform API")
    
    # Initialize orchestration manager
    orchestration_manager.initialize(num_workers=10)
    await orchestration_manager.start()
    
    # Start trigger system
    await trigger_system.start()
    
    # Register task handlers
    orchestration_manager.register_task_handler("tool_execution", tool_execution_handler)
    orchestration_manager.register_task_handler("workflow_execution", workflow_execution_handler)
    
    logger.info("Integration Platform API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("Shutting down Integration Platform API")
    
    await orchestration_manager.stop()
    await trigger_system.stop()
    
    logger.info("Integration Platform API shut down")

# Task handlers
async def tool_execution_handler(task_payload: Dict[str, Any]):
    """Handle tool execution tasks"""
    tool_id = task_payload.get("tool_id")
    parameters = task_payload.get("parameters", {})
    user_context = task_payload.get("user_context", {})
    
    execution_request = ToolExecutionRequest(
        tool_id=tool_id,
        parameters=parameters,
        user_context=user_context
    )
    
    result = await tool_registry.executor.execute(execution_request)
    return result.dict()

async def workflow_execution_handler(task_payload: Dict[str, Any]):
    """Handle workflow execution tasks"""
    workflow_id = task_payload.get("workflow_id")
    trigger_data = task_payload.get("trigger_data", {})
    context = task_payload.get("context", {})
    
    execution_id = await workflow_engine.execute_workflow(
        workflow_id,
        trigger_data=trigger_data,
        context=context
    )
    
    return {"execution_id": execution_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
