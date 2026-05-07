"""
Full API Server - Start with platform components initialized
"""

import os
import asyncio
import uvicorn
from api.routes.main_api import app
from tools.registry.tool_registry import tool_registry
from connectors.examples.slack_connector import SlackConnector
from connectors.examples.http_connector import HTTPConnector

def initialize_components():
    """Initialize platform components synchronously"""
    print("Initializing Integration Platform components...")
    
    # Register example connectors
    slack_connector = SlackConnector()
    http_connector = HTTPConnector()
    
    # Register tools from connectors
    slack_actions = slack_connector.get_actions()
    http_actions = http_connector.get_actions()
    
    # Create tool definitions from actions
    from tools.registry.tool_registry import ToolDefinition
    
    for action_name, action_def in slack_actions.items():
        tool = ToolDefinition(
            id=f"slack_{action_name}",
            name=action_def.name,
            description=action_def.description,
            category="communication",  # Use valid category
            input_schema=action_def.input_schema,
            output_schema=action_def.output_schema,
            connector_name="slack",
            action_name=action_name,
            connector_action=action_name  # Use string instead of object
        )
        tool_registry.register_tool(tool)
        print(f"Registered tool: {tool.name} (Slack)")
    
    for action_name, action_def in http_actions.items():
        tool = ToolDefinition(
            id=f"http_{action_name}",
            name=action_def.name,
            description=action_def.description,
            category="general",  # Use valid category
            input_schema=action_def.input_schema,
            output_schema=action_def.output_schema,
            connector_name="http",
            action_name=action_name,
            connector_action=action_name  # Use string instead of object
        )
        tool_registry.register_tool(tool)
        print(f"Registered tool: {tool.name} (HTTP)")
    
    print(f"Platform initialized with {len(tool_registry.list_tools())} tools")
    return True

if __name__ == "__main__":
    try:
        # Initialize components
        initialize_components()
        
        # Print startup information
        print("=" * 50)
        print("Integration Platform API is ready!")
        print("=" * 50)
        print("API Documentation: http://localhost:8000/docs")
        print("Health Check: http://localhost:8000/health")
        print("System Info: http://localhost:8000/api/system/info")
        print("Tools Available:", len(tool_registry.list_tools()))
        print("=" * 50)
        
        # Start API server with port conflict resolution
        port = int(os.getenv("API_PORT", "8000"))
        max_port = port + 10  # Try ports 8000-8010
        
        for current_port in range(port, max_port + 1):
            try:
                print(f"Trying to start server on port {current_port}...")
                uvicorn.run(
                    app,
                    host=os.getenv("API_HOST", "0.0.0.0"),
                    port=current_port,
                    log_level="info"
                )
                break
            except OSError as e:
                if "Address already in use" in str(e) and current_port < max_port:
                    print(f"Port {current_port} is in use, trying next port...")
                    continue
                else:
                    raise e
        
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"Startup failed: {str(e)}")
