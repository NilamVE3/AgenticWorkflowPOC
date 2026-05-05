"""
Tool registry for managing and discovering available tools
"""

from typing import Dict, List, Any, Type
from agent_system.agent import AgentTool, RealTimeConnection, engine
import importlib
import os
import logging

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Registry for managing agent tools"""
    
    def __init__(self):
        self.tools: Dict[str, AgentTool] = {}
        self.tool_classes: Dict[str, Type[AgentTool]] = {}
        
    def register_tool(self, tool: AgentTool):
        """Register a tool instance"""
        self.tools[tool.name] = tool
        engine.register_tool(tool)
        logger.info(f"Registered tool: {tool.name}")
        
    def register_tool_class(self, tool_class: Type[AgentTool], **kwargs):
        """Register a tool class and instantiate it"""
        tool_instance = tool_class(**kwargs)
        self.register_tool(tool_instance)
        self.tool_classes[tool_class.__name__] = tool_class
        
    def get_tool(self, name: str) -> AgentTool:
        """Get a tool by name"""
        return self.tools.get(name)
        
    def get_all_tools(self) -> Dict[str, AgentTool]:
        """Get all registered tools"""
        return self.tools.copy()
        
    def get_tool_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all tools"""
        tools_info = {}
        for name, tool in self.tools.items():
            try:
                tools_info[name] = {
                    'name': tool.name,
                    'description': tool.description,
                    'parameters': tool.parameters,
                    'is_realtime': tool.is_realtime
                }
            except Exception as e:
                # If tool fails to provide info, provide basic info
                tools_info[name] = {
                    'name': name,
                    'description': 'Tool available (auth may be required)',
                    'parameters': {},
                    'is_realtime': False,
                    'error': str(e)
                }
        return tools_info
        
    def load_single_tool(self, directory: str, filename: str):
        """Load a single tool from a Python module"""
        if not os.path.exists(os.path.join(directory, filename)):
            logger.warning(f"Tool file does not exist: {filename}")
            return
            
        try:
            module_name = filename[:-3]
            spec = importlib.util.spec_from_file_location(
                module_name, 
                os.path.join(directory, filename)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for tool classes in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, AgentTool) and 
                    attr != AgentTool):
                    # Instantiate and register the tool
                    self.register_tool_class(attr)
                    
        except Exception as e:
            logger.error(f"Failed to load tool from {filename}: {e}")

    def load_tools_from_directory(self, directory: str):
        """Load tools from a directory of Python modules"""
        if not os.path.exists(directory):
            logger.warning(f"Tools directory does not exist: {directory}")
            return
            
        for filename in os.listdir(directory):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = filename[:-3]
                try:
                    # Import the module
                    spec = importlib.util.spec_from_file_location(
                        module_name, 
                        os.path.join(directory, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Look for tool classes in the module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, AgentTool) and 
                            attr != AgentTool):
                            # Instantiate and register the tool
                            self.register_tool_class(attr)
                            
                except Exception as e:
                    logger.error(f"Failed to load tools from {filename}: {e}")
                    
    def unregister_tool(self, name: str):
        """Unregister a tool"""
        if name in self.tools:
            del self.tools[name]
            if name in engine.tools:
                del engine.tools[name]
            logger.info(f"Unregistered tool: {name}")

# Global tool registry instance
tool_registry = ToolRegistry()

def register_integrations():
    """Register all available integrations"""
    # Only load safe tools that don't require authentication
    tools_dir = os.path.join(os.path.dirname(__file__), 'tools')
    safe_tools = ['file_tools.py', 'api_tools.py', 'database_tools.py']
    
    for filename in safe_tools:
        if os.path.exists(os.path.join(tools_dir, filename)):
            logger.info(f"Loading safe tool: {filename}")
            tool_registry.load_single_tool(tools_dir, filename)
    
    # Load connectors from the connectors directory
    connectors_dir = os.path.join(os.path.dirname(__file__), 'connectors')
    if os.path.exists(connectors_dir):
        for filename in os.listdir(connectors_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = filename[:-3]
                try:
                    spec = importlib.util.spec_from_file_location(
                        module_name,
                        os.path.join(connectors_dir, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Look for connection classes
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, RealTimeConnection) and 
                            attr != RealTimeConnection):
                            # Only register connection class, don't instantiate yet
                            # connection = attr()  # Don't auto-instantiate
                            # engine.register_connection(connection)  # Don't auto-register
                            pass
                            
                except Exception as e:
                    logger.error(f"Failed to load connector from {filename}: {e}")
