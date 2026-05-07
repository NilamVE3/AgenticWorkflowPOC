"""
Clean Startup Script - Handles port conflicts and process cleanup
"""

import os
import subprocess
import time
import socket
import uvicorn
from api.routes.main_api import app
from tools.registry.tool_registry import tool_registry
from connectors.examples.slack_connector import SlackConnector
from connectors.examples.http_connector import HTTPConnector
from tools.registry.tool_registry import ToolDefinition

def is_port_available(port):
    """Check if a port is available"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            return True
    except OSError:
        return False

def kill_processes_on_port(port):
    """Kill all processes using the specified port"""
    try:
        # Find processes using the port
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        pids_to_kill = []
        for line in lines:
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid.isdigit():
                        pids_to_kill.append(pid)
        
        # Kill the processes
        for pid in set(pids_to_kill):  # Remove duplicates
            try:
                subprocess.run(['taskkill', '/PID', pid, '/F'], capture_output=True)
                print(f"Killed process {pid} using port {port}")
            except:
                pass
        
        # Wait a moment for processes to terminate
        time.sleep(1)
        
    except Exception as e:
        print(f"Error killing processes: {e}")

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
    for action_name, action_def in slack_actions.items():
        tool = ToolDefinition(
            id=f"slack_{action_name}",
            name=action_def.name,
            description=action_def.description,
            category="communication",
            input_schema=action_def.input_schema,
            output_schema=action_def.output_schema,
            connector_name="slack",
            action_name=action_name,
            connector_action=action_name
        )
        tool_registry.register_tool(tool)
        print(f"Registered tool: {tool.name} (Slack)")
    
    for action_name, action_def in http_actions.items():
        tool = ToolDefinition(
            id=f"http_{action_name}",
            name=action_def.name,
            description=action_def.description,
            category="general",
            input_schema=action_def.input_schema,
            output_schema=action_def.output_schema,
            connector_name="http",
            action_name=action_name,
            connector_action=action_name
        )
        tool_registry.register_tool(tool)
        print(f"Registered tool: {tool.name} (HTTP)")
    
    print(f"Platform initialized with {len(tool_registry.list_tools())} tools")
    return True

def find_available_port(start_port=8000, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        if is_port_available(port):
            return port
    return None

def main():
    try:
        # Initialize components
        initialize_components()
        
        # Find available port
        port = find_available_port(8000, 10)
        if not port:
            print("No available ports found in range 8000-8010")
            return
        
        # Kill any remaining processes on the found port
        kill_processes_on_port(port)
        
        # Wait a moment
        time.sleep(1)
        
        # Print startup information
        print("=" * 50)
        print("Integration Platform API is ready!")
        print("=" * 50)
        print(f"API Documentation: http://localhost:{port}/docs")
        print(f"Health Check: http://localhost:{port}/health")
        print(f"System Info: http://localhost:{port}/api/system/info")
        print(f"Tools Available: {len(tool_registry.list_tools())}")
        print("=" * 50)
        
        # Create a simple UI server script with the correct port
        ui_script = f"""
# UI Server with correct API port
import os
import uvicorn
from ui.server import run_ui_server

if __name__ == "__main__":
    print("Starting UI Server...")
    print("API Backend: http://localhost:{port}")
    print("Web Interface: http://localhost:3000")
    run_ui_server(host="0.0.0.0", port=3000)
"""
        
        with open('start_ui_with_port.py', 'w') as f:
            f.write(ui_script)
        
        print(f"Created start_ui_with_port.py for UI server")
        print(f"Run: python start_ui_with_port.py (in separate terminal)")
        
        # Start API server
        uvicorn.run(
            app,
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=port,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"Startup failed: {str(e)}")

if __name__ == "__main__":
    main()
