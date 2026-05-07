"""
Main entry point for the Integration Platform
"""

import asyncio
import logging
import os
from pathlib import Path

# Add the integration_platform directory to Python path
current_dir = Path(__file__).parent
import sys
sys.path.insert(0, str(current_dir))

from api.routes.main_api import app
from tools.registry.tool_registry import tool_registry
from workflows.engine.workflow_engine import workflow_engine
from orchestration.queue.task_queue import orchestration_manager
from triggers.trigger_system import trigger_system
from auth.auth_service import auth_service
from agents.llm.agentic_layer import agentic_layer
from connectors.sdk.base_connector import connector_registry

# Import example connectors
from connectors.examples.slack_connector import SlackConnector
from connectors.examples.http_connector import HTTPConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def initialize_platform():
    """Initialize all platform components"""
    logger.info("Initializing Integration Platform...")
    
    # Initialize agentic layer with tool registry and workflow engine
    agentic_layer.tool_registry = tool_registry
    agentic_layer.workflow_engine = workflow_engine
    
    # Register example connectors
    connector_registry.register(SlackConnector)
    connector_registry.register(HTTPConnector)
    
    # Initialize orchestration manager
    orchestration_manager.initialize(num_workers=10)
    
    # Start all services
    await orchestration_manager.start()
    await trigger_system.start()
    
    # Register task handlers
    orchestration_manager.register_task_handler("tool_execution", tool_execution_handler)
    orchestration_manager.register_task_handler("workflow_execution", workflow_execution_handler)
    
    # Add event handler for triggers
    trigger_system.add_event_handler(trigger_event_handler)
    
    logger.info("Integration Platform initialized successfully")

async def tool_execution_handler(task_payload):
    """Handle tool execution tasks"""
    from tools.registry.tool_registry import ToolExecutionRequest
    
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

async def workflow_execution_handler(task_payload):
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

async def trigger_event_handler(event):
    """Handle trigger events"""
    logger.info(f"Received trigger event: {event.trigger_id}")
    
    # If the trigger is associated with a workflow, execute it
    if event.workflow_id:
        try:
            execution_id = await workflow_engine.execute_workflow(
                event.workflow_id,
                trigger_data=event.data,
                context={"trigger_event_id": event.event_id}
            )
            logger.info(f"Started workflow execution: {execution_id}")
        except Exception as e:
            logger.error(f"Failed to execute workflow for trigger {event.trigger_id}: {str(e)}")

def create_sample_tools():
    """Create some sample tools for demonstration"""
    from tools.registry.tool_registry import ToolDefinition, ToolCategory, ToolParameter
    
    # Sample HTTP GET tool
    http_get_tool = ToolDefinition(
        name="http_get_request",
        description="Make HTTP GET request",
        category=ToolCategory.GENERAL,
        connector_name="http",
        connector_action="get_request",
        parameters=[
            ToolParameter(
                name="endpoint",
                type="string",
                description="API endpoint path",
                required=True
            ),
            ToolParameter(
                name="params",
                type="object",
                description="Query parameters",
                required=False
            )
        ]
    )
    
    # Sample Slack message tool
    slack_message_tool = ToolDefinition(
        name="slack_send_message",
        description="Send message to Slack channel",
        category=ToolCategory.COMMUNICATION,
        connector_name="slack",
        connector_action="send_message",
        parameters=[
            ToolParameter(
                name="channel",
                type="string",
                description="Channel ID or name",
                required=True
            ),
            ToolParameter(
                name="message",
                type="string",
                description="Message to send",
                required=True
            )
        ]
    )
    
    # Register tools
    tool_registry.register_tool(http_get_tool)
    tool_registry.register_tool(slack_message_tool)

def load_sample_workflows():
    """Load sample workflows from JSON file"""
    try:
        import json
        from workflows.engine.workflow_engine import WorkflowDefinition, WorkflowStep, StepType
        
        workflows_file = current_dir / "examples" / "sample_workflows.json"
        
        if workflows_file.exists():
            with open(workflows_file, 'r') as f:
                sample_workflows = json.load(f)
            
            for workflow_data in sample_workflows.get("sample_workflows", []):
                # Convert JSON steps to WorkflowStep objects
                steps = []
                for step_data in workflow_data.get("steps", []):
                    step = WorkflowStep(
                        id=step_data["id"],
                        name=step_data["name"],
                        type=StepType(step_data["type"]),
                        config=step_data["config"],
                        depends_on=step_data.get("depends_on", [])
                    )
                    steps.append(step)
                
                # Create workflow definition
                workflow_def = WorkflowDefinition(
                    name=workflow_data["name"],
                    description=workflow_data.get("description"),
                    steps=steps,
                    trigger=workflow_data.get("trigger", {})
                )
                
                # Register workflow
                workflow_engine.register_workflow(workflow_def)
                logger.info(f"Loaded sample workflow: {workflow_data['name']}")
        
    except Exception as e:
        logger.error(f"Failed to load sample workflows: {str(e)}")

async def main():
    """Main entry point"""
    try:
        # Initialize platform
        await initialize_platform()
        
        # Create sample tools
        create_sample_tools()
        
        # Load sample workflows
        load_sample_workflows()
        
        # Print startup information
        logger.info("=" * 50)
        logger.info("Integration Platform is ready!")
        logger.info("=" * 50)
        logger.info("API Documentation: http://localhost:8000/docs")
        logger.info("Health Check: http://localhost:8000/health")
        logger.info("System Info: http://localhost:8000/api/system/info")
        logger.info("=" * 50)
        
        # Start of FastAPI app
        import uvicorn
        import threading
        
        # Start UI server in a separate thread
        def start_ui_server():
            from ui.server import run_ui_server
            run_ui_server(
                host=os.getenv("UI_HOST", "0.0.0.0"),
                port=int(os.getenv("UI_PORT", "3000"))
            )
        
        ui_thread = threading.Thread(target=start_ui_server, daemon=True)
        ui_thread.start()
        
        try:
            # Start API server
            uvicorn.run(
                app,
                host=os.getenv("API_HOST", "0.0.0.0"),
                port=int(os.getenv("API_PORT", "8000")),
                log_level="info"
            )
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            # Cleanup
            await orchestration_manager.stop()
            await trigger_system.stop()
            logger.info("Integration Platform shut down")
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
    finally:
        # Cleanup
        await orchestration_manager.stop()
        await trigger_system.stop()
        logger.info("Integration Platform shut down")

if __name__ == "__main__":
    asyncio.run(main())
