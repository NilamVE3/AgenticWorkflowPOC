"""
Main entry point for the agent system
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_system.agent import engine, AgentExecutionEngine
from agent_system.tool_registry import ToolRegistry, tool_registry, register_integrations
from agent_system.schemas import AgentConfig, SystemStatus
import importlib

# Configure logging with DEBUG level for detailed debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AgentSystem:
    """Main agent system orchestrator"""
    
    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self.engine = engine
        self.tool_registry = tool_registry
        self.start_time = datetime.now()
        
    def initialize(self):
        """Initialize the agent system"""
        logger.info("Initializing Agent System...")
        logger.debug(f"Config: {self.config}")
        
        # Register built-in tools
        self._register_builtin_tools()
        
        # Register integrations from tools and connectors directories
        if self.config.auto_register_tools:
            try:
                logger.debug("Auto-registering integrations...")
                register_integrations()
                logger.info("Integrations registered successfully")
            except Exception as e:
                logger.warning(f"Failed to register integrations: {e}")
                logger.debug(f"Integration registration error details:", exc_info=True)
        
        # Register built-in connections
        self._register_builtin_connections()
        
        logger.info("Agent System initialized successfully")
        logger.debug(f"Engine state - Tools: {len(self.engine.tools)}, Connections: {len(self.engine.connections)}")
        
    def _register_builtin_tools(self):
        """Register built-in tools"""
        logger.debug("Registering built-in tools...")
        from tools.file_tools import FileOperationTool
        from tools.api_tools import APICallTool
        from tools.database_tools import DatabaseTool
        
        # Only register tools that don't require authentication
        self.tool_registry.register_tool(FileOperationTool())
        self.tool_registry.register_tool(APICallTool())
        self.tool_registry.register_tool(DatabaseTool())
        
        # Don't register Slack, Gmail, Weather tools by default (they need auth)
        logger.info("Built-in tools registered (auth-requiring tools skipped)")
        logger.debug(f"Registered tools: {list(self.tool_registry.tools.keys())}")
        
    def _register_builtin_connections(self):
        """Register built-in connections"""
        logger.debug("Registering built-in connections...")
        from connectors.websocket import WebSocketConnection
        from connectors.redis import RedisConnection
        
        # Only register connection classes, don't instantiate to avoid auth errors
        # self.engine.register_connection(WebSocketConnection())
        # self.engine.register_connection(RedisConnection())
        logger.info("Built-in connections registered (not auto-instantiated)")
        logger.debug(f"Available connection classes: WebSocketConnection, RedisConnection")
        
    def get_system_status(self) -> SystemStatus:
        """Get current system status"""
        uptime = datetime.now() - self.start_time
        
        return SystemStatus(
            agent_status="running",
            total_tools=len(self.engine.tools),
            active_connections=len([c for c in self.engine.connections.values() if c.is_connected]),
            active_tasks=len(self.engine.active_tasks),
            uptime=str(uptime)
        )
    
    def execute_task(self, tool: str, parameters: Dict[str, Any] = None, description: str = None) -> str:
        """Execute a task"""
        task = {
            'tool': tool,
            'parameters': parameters or {},
            'description': description
        }
        return self.engine.execute_task(task)
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status"""
        if task_id in self.engine.active_tasks:
            task = self.engine.active_tasks[task_id]
            return {
                'task_id': task_id,
                'status': task['status'],
                'start_time': task['start_time'].isoformat(),
                'result': task.get('result'),
                'error': task.get('error')
            }
        else:
            # Check in history
            for task in self.engine.execution_history:
                if task.get('task_id') == task_id:
                    return {
                        'task_id': task_id,
                        'status': task['status'],
                        'start_time': task['start_time'].isoformat(),
                        'end_time': task.get('end_time', {}).isoformat() if task.get('end_time') else None,
                        'result': task.get('result'),
                        'error': task.get('error')
                    }
            return {"error": "Task not found"}
    
    def list_tools(self) -> Dict[str, Any]:
        """List all available tools"""
        return self.tool_registry.get_tool_info()
    
    def list_connections(self) -> Dict[str, Any]:
        """List all connections"""
        connections_info = {}
        for name, conn in self.engine.connections.items():
            connections_info[name] = {
                'name': conn.name,
                'type': conn.connection_type,
                'is_connected': conn.is_connected,
                'last_activity': conn.last_activity.isoformat() if conn.last_activity else None
            }
        return connections_info
    
    def shutdown(self):
        """Shutdown the agent system"""
        logger.info("Shutting down Agent System...")
        
        # Disconnect all connections
        for connection in self.engine.connections.values():
            if connection.is_connected:
                connection.disconnect()
        
        logger.info("Agent System shutdown complete")

def main():
    """Main function to run the agent system"""
    print("🤖 Agent System Starting...")
    
    # Create and initialize the agent system
    agent_system = AgentSystem()
    
    try:
        agent_system.initialize()
        
        # Display system status
        status = agent_system.get_system_status()
        print(f"✅ Agent System Ready!")
        print(f"   - Tools: {status.total_tools}")
        print(f"   - Active Connections: {status.active_connections}")
        print(f"   - Uptime: {status.uptime}")
        
        # Interactive mode
        print("\n🎯 Agent System Interactive Mode")
        print("Available commands:")
        print("  list_tools - List all available tools")
        print("  list_connections - List all connections")
        print("  execute <tool> [params] - Execute a tool")
        print("  status <task_id> - Get task status")
        print("  quit - Exit the system")
        print()
        
        while True:
            try:
                command = input("agent> ").strip()
                
                if not command:
                    continue
                    
                if command == 'quit':
                    break
                elif command == 'list_tools':
                    tools = agent_system.list_tools()
                    print("\n📦 Available Tools:")
                    for name, info in tools.items():
                        print(f"  - {name}: {info['description']}")
                        if info.get('is_realtime'):
                            print(f"    ⚡ Real-time enabled")
                    print()
                    
                elif command == 'list_connections':
                    connections = agent_system.list_connections()
                    print("\n🔗 Connections:")
                    for name, info in connections.items():
                        status_icon = "✅" if info['is_connected'] else "❌"
                        print(f"  - {name} ({info['type']}) {status_icon}")
                    print()
                    
                elif command.startswith('execute '):
                    parts = command.split(' ', 2)
                    if len(parts) >= 2:
                        tool_name = parts[1]
                        params_str = parts[2] if len(parts) > 2 else "{}"
                        
                        try:
                            import json
                            params = json.loads(params_str) if params_str else {}
                        except:
                            params = {}
                            
                        task_id = agent_system.execute_task(tool_name, params)
                        print(f"🚀 Task submitted: {task_id}")
                        
                        # Wait a moment and check status
                        import time
                        time.sleep(1)
                        status = agent_system.get_task_status(task_id)
                        print(f"📊 Status: {status['status']}")
                        if status.get('result'):
                            print(f"📤 Result: {status['result']}")
                        elif status.get('error'):
                            print(f"❌ Error: {status['error']}")
                    else:
                        print("Usage: execute <tool_name> [json_params]")
                        
                elif command.startswith('status '):
                    task_id = command.split(' ', 1)[1]
                    status = agent_system.get_task_status(task_id)
                    print(f"📊 Task Status: {status}")
                    
                else:
                    print("Unknown command. Type 'quit' to exit.")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
    finally:
        agent_system.shutdown()
        print("👋 Agent System Shutdown Complete")

if __name__ == "__main__":
    main()
