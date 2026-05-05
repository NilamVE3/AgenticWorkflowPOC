from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import json
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Callable
import logging
import os
import importlib.util

# Import agent system components
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agent_system'))

from main import AgentSystem

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize agent system
agent_system = AgentSystem()
agent_system.initialize()

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tools', methods=['GET'])
def get_tools():
    """Get list of available tools"""
    logger.info("GET /api/tools - Fetching available tools")
    try:
        tools = agent_system.list_tools()
        logger.debug(f"Found {len(tools)} tools")
        return jsonify(tools)
    except Exception as e:
        logger.error(f"Error fetching tools: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/connections', methods=['GET'])
def get_connections():
    """Get list of available connections"""
    logger.info("GET /api/connections - Fetching connections")
    try:
        connections = agent_system.list_connections()
        logger.debug(f"Found {len(connections)} connections")
        return jsonify(connections)
    except Exception as e:
        logger.error(f"Error fetching connections: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/available-connectors', methods=['GET'])
def get_available_connectors():
    """Get list of all available connectors in the system"""
    logger.info("GET /api/available-connectors - Fetching available connectors")
    try:
        connectors_dir = os.path.join(os.path.dirname(__file__), 'agent_system', 'connectors')
        available_connectors = []
        
        if os.path.exists(connectors_dir):
            for filename in os.listdir(connectors_dir):
                if filename.endswith('.py') and not filename.startswith('__'):
                    module_name = filename[:-3]
                    
                    # Try to get connector info
                    try:
                        spec = importlib.util.spec_from_file_location(
                            module_name,
                            os.path.join(connectors_dir, filename)
                        )
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # Look for connector classes
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if (hasattr(attr, '__bases__') and 
                                any('RealTimeConnection' in base.__name__ for base in attr.__bases__) and
                                attr.__name__ != 'RealTimeConnection'):
                                
                                connector_info = {
                                    'name': attr.__name__,
                                    'module': module_name,
                                    'class': attr_name,
                                    'description': attr.__doc__ or f"{attr.__name__} connector",
                                    'type': getattr(attr, 'connection_type', 'Unknown'),
                                    'is_registered': attr.__name__ in [type(c).__name__ for c in agent_system.engine.connections.values()]
                                }
                                available_connectors.append(connector_info)
                                break
                                
                    except Exception as e:
                        logger.error(f"Error loading connector {filename}: {e}")
                        available_connectors.append({
                            'name': module_name,
                            'module': module_name,
                            'class': 'Unknown',
                            'description': f"Error loading: {str(e)}",
                            'type': 'Unknown',
                            'is_registered': False,
                            'error': str(e)
                        })
        
        return jsonify(available_connectors)
        
    except Exception as e:
        logger.error(f"Error getting available connectors: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/register-connector', methods=['POST'])
def register_connector():
    """Register a new connector"""
    logger.info("POST /api/register-connector - Registering new connector")
    try:
        data = request.json
        logger.debug(f"Registration data: {data}")
        
        connector_name = data.get('connector_name')
        module_name = data.get('module_name')
        class_name = data.get('class_name')
        config = data.get('config', {})
        
        logger.debug(f"Connector details - Name: {connector_name}, Module: {module_name}, Class: {class_name}")
        
        if not connector_name or not module_name or not class_name:
            error_msg = "Missing required parameters"
            logger.error(f"Registration failed: {error_msg}")
            return jsonify({"error": error_msg}), 400
        
        # Import the connector module
        connectors_dir = os.path.join(os.path.dirname(__file__), 'agent_system', 'connectors')
        module_path = os.path.join(connectors_dir, f"{module_name}.py")
        
        logger.debug(f"Looking for module at: {module_path}")
        
        if not os.path.exists(module_path):
            error_msg = f"Connector module {module_name} not found"
            logger.error(f"Registration failed: {error_msg}")
            return jsonify({"error": error_msg}), 404
        
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get the connector class
        if not hasattr(module, class_name):
            error_msg = f"Class {class_name} not found in module {module_name}"
            logger.error(f"Registration failed: {error_msg}")
            return jsonify({"error": error_msg}), 404
        
        connector_class = getattr(module, class_name)
        
        # Instantiate and register the connector
        logger.debug(f"Instantiating connector class: {class_name}")
        connector_instance = connector_class(config)
        logger.debug(f"Registering connector instance: {connector_instance.name}")
        agent_system.engine.register_connection(connector_instance)
        
        logger.info(f"Successfully registered connector: {connector_name}")
        
        return jsonify({
            "success": True,
            "message": f"Connector {connector_name} registered successfully",
            "connector": {
                "name": connector_instance.name,
                "type": connector_instance.connection_type,
                "is_connected": connector_instance.is_connected
            }
        })
        
    except Exception as e:
        logger.error(f"Error registering connector: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/unregister-connector', methods=['POST'])
def unregister_connector():
    """Unregister a connector"""
    try:
        data = request.json
        connector_name = data.get('connector_name')
        
        if not connector_name:
            return jsonify({"error": "Connector name is required"}), 400
        
        if connector_name in agent_system.engine.connections:
            # Disconnect before unregistering
            connection = agent_system.engine.connections[connector_name]
            if connection.is_connected:
                connection.disconnect()
            
            del agent_system.engine.connections[connector_name]
            logger.info(f"Unregistered connector: {connector_name}")
            
            return jsonify({
                "success": True,
                "message": f"Connector {connector_name} unregistered successfully"
            })
        else:
            return jsonify({"error": f"Connector {connector_name} not found"}), 404
            
    except Exception as e:
        logger.error(f"Error unregistering connector: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/connector-config', methods=['GET'])
def get_connector_config():
    """Get configuration schema for a connector"""
    try:
        connector_name = request.args.get('connector')
        if not connector_name:
            return jsonify({"error": "Connector name is required"}), 400
        
        # Get connector info from available connectors
        available_connectors = get_available_connectors().get_json()
        connector_info = None
        
        for conn in available_connectors:
            if conn['name'] == connector_name:
                connector_info = conn
                break
        
        if not connector_info:
            return jsonify({"error": f"Connector {connector_name} not found"}), 404
        
        # Return configuration schema (this could be enhanced with actual schema)
        config_schema = {
            "name": connector_name,
            "description": connector_info['description'],
            "type": connector_info['type'],
            "config_fields": [
                {
                    "name": "enabled",
                    "type": "boolean",
                    "description": "Enable this connector",
                    "default": False
                }
            ]
        }
        
        # Add specific config fields based on connector type
        if connector_name.lower() == 'slackconnection':
            config_schema["config_fields"].extend([
                {
                    "name": "bot_token",
                    "type": "string",
                    "description": "Slack bot token",
                    "required": True,
                    "sensitive": True
                },
                {
                    "name": "user_token",
                    "type": "string", 
                    "description": "Slack user token (optional)",
                    "required": False,
                    "sensitive": True
                }
            ])
        elif connector_name.lower() == 'gmailconnection':
            config_schema["config_fields"].extend([
                {
                    "name": "client_id",
                    "type": "string",
                    "description": "Gmail client ID",
                    "required": True
                },
                {
                    "name": "client_secret",
                    "type": "string",
                    "description": "Gmail client secret",
                    "required": True,
                    "sensitive": True
                },
                {
                    "name": "access_token",
                    "type": "string",
                    "description": "Gmail access token",
                    "required": False,
                    "sensitive": True
                }
            ])
        elif connector_name.lower() == 'weatherconnection':
            config_schema["config_fields"].extend([
                {
                    "name": "api_key",
                    "type": "string",
                    "description": "Weather API key",
                    "required": True,
                    "sensitive": True
                },
                {
                    "name": "default_location",
                    "type": "string",
                    "description": "Default location for weather",
                    "required": False
                }
            ])
        
        return jsonify(config_schema)
        
    except Exception as e:
        logger.error(f"Error getting connector config: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create and execute a new task"""
    task_data = request.json
    if not task_data:
        return jsonify({"error": "No task data provided"}), 400
        
    task_id = agent_system.execute_task(
        tool=task_data.get('tool'),
        parameters=task_data.get('parameters', {}),
        description=task_data.get('description')
    )
    return jsonify({"task_id": task_id, "status": "submitted"})

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get status of a specific task"""
    status = agent_system.get_task_status(task_id)
    if 'error' in status:
        return jsonify(status), 404
    return jsonify(status)

@app.before_request
def log_request_info():
    """Log incoming request details for debugging"""
    logger.debug(f"Incoming request: {request.method} {request.url}")
    logger.debug(f"Headers: {dict(request.headers)}")
    logger.debug(f"Args: {dict(request.args)}")
    if request.is_json:
        try:
            logger.debug(f"JSON Body: {request.get_json()}")
        except:
            logger.debug("JSON Body: [invalid or empty]")

@app.after_request
def after_request(response):
    """Handle response logging and CORS headers"""
    # Log response details for debugging
    logger.debug(f"Response status: {response.status_code}")
    logger.debug(f"Response headers: {dict(response.headers)}")
    if response.status_code >= 400:
        logger.error(f"Error response body: {response.get_data(as_text=True)}")
    
    # Add CORS headers
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    return response

@app.route('/api/connection-action', methods=['POST'])
def connection_action():
    """Handle connection actions (connect/disconnect/configure)"""
    try:
        data = request.json
        connection_name = data.get('connection')
        action = data.get('action')
        config = data.get('config', {})
        
        if not connection_name or not action:
            return jsonify({"error": "Connection name and action are required"}), 400
        
        connection = agent_system.engine.connections.get(connection_name)
        if not connection:
            return jsonify({"error": f"Connection {connection_name} not found"}), 404
        
        # Configure connection if config is provided
        if config and hasattr(connection, 'configure'):
            if not connection.configure(config):
                return jsonify({"error": f"Failed to configure connection {connection_name}"}), 400
        
        # Perform action
        if action == 'connect':
            success = connection.connect()
            return jsonify({
                "success": success,
                "status": "connected" if success else "failed",
                "message": f"Connection {connection_name} {'established' if success else 'failed'}"
            })
        elif action == 'disconnect':
            connection.disconnect()
            return jsonify({
                "success": True,
                "status": "disconnected",
                "message": f"Connection {connection_name} disconnected"
            })
        elif action == 'configure':
            # Configuration already handled above
            return jsonify({
                "success": True,
                "status": "configured",
                "message": f"Connection {connection_name} configured successfully"
            })
        else:
            return jsonify({"error": f"Unknown action: {action}"}), 400
            
    except Exception as e:
        logger.error(f"Error in connection action: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks', methods=['GET'])
def get_all_tasks():
    """Get all tasks (active and completed)"""
    try:
        # Get active tasks
        active_tasks = []
        for task_id, task in agent_system.engine.active_tasks.items():
            active_tasks.append({
                'task_id': task_id,
                'status': task['status'],
                'start_time': task['start_time'].isoformat(),
                'task': task['task'],
                'result': task.get('result'),
                'error': task.get('error')
            })
        
        # Get completed tasks from history
        completed_tasks = []
        for task in agent_system.engine.execution_history[-10:]:  # Last 10 tasks
            completed_tasks.append({
                'task_id': task.get('task_id', 'unknown'),
                'status': task['status'],
                'start_time': task['start_time'].isoformat(),
                'end_time': task.get('end_time', {}).isoformat() if task.get('end_time') else None,
                'task': task['task'],
                'result': task.get('result'),
                'error': task.get('error')
            })
        
        all_tasks = active_tasks + completed_tasks
        return jsonify(all_tasks)
        
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return jsonify({"error": str(e)}), 500

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    emit('connected', {'message': 'Connected to Agent Execution Server'})
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('execute_tool')
def handle_execute_tool(data):
    """Execute tool directly via WebSocket"""
    tool_name = data.get('tool')
    parameters = data.get('parameters', {})
    
    tools = agent_system.list_tools()
    if tool_name not in tools:
        emit('tool_error', {'error': f'Tool {tool_name} not found'})
        return
    
    try:
        task_id = agent_system.execute_task(tool_name, parameters)
        emit('tool_result', {'tool': tool_name, 'task_id': task_id})
    except Exception as e:
        emit('tool_error', {'tool': tool_name, 'error': str(e)})

@socketio.on('connection_action')
def handle_connection_action(data):
    """Handle connection actions (connect/disconnect/configure)"""
    connection_name = data.get('connection')
    action = data.get('action')
    config = data.get('config', {})
    
    connections = agent_system.list_connections()
    if connection_name not in connections:
        emit('connection_error', {'error': f'Connection {connection_name} not found'})
        return
    
    connection = agent_system.engine.connections.get(connection_name)
    if not connection:
        emit('connection_error', {'error': f'Connection {connection_name} not found in engine'})
        return
    
    try:
        # Configure connection if config is provided
        if config and hasattr(connection, 'configure'):
            if not connection.configure(config):
                emit('connection_error', {'error': f'Failed to configure connection {connection_name}'})
                return
        
        if action == 'connect':
            success = connection.connect()
            emit('connection_status', {
                'connection': connection_name,
                'status': 'connected' if success else 'failed'
            })
        elif action == 'disconnect':
            connection.disconnect()
            emit('connection_status', {
                'connection': connection_name,
                'status': 'disconnected'
            })
        elif action == 'configure':
            emit('connection_status', {
                'connection': connection_name,
                'status': 'configured'
            })
        else:
            emit('connection_error', {'error': f'Unknown action: {action}'})
            
    except Exception as e:
        emit('connection_error', {'connection': connection_name, 'error': str(e)})

@socketio.on('connection-action', namespace='/api')
def connection_action(data):
    """Handle connection actions (connect/disconnect/configure)"""
    try:
        connection_name = data.get('connection')
        action = data.get('action')
        config = data.get('config', {})
        
        if not connection_name or not action:
            return jsonify({"error": "Connection name and action are required"}), 400
        
        connection = agent_system.engine.connections.get(connection_name)
        if not connection:
            return jsonify({"error": f"Connection {connection_name} not found"}), 404
        
        # Configure connection if config is provided
        if config and hasattr(connection, 'configure'):
            if not connection.configure(config):
                return jsonify({"error": f"Failed to configure connection {connection_name}"}), 400
        
        # Perform action
        if action == 'connect':
            success = connection.connect()
            return jsonify({
                "success": success,
                "status": "connected" if success else "failed",
                "message": f"Connection {connection_name} {'established' if success else 'failed'}"
            })
        elif action == 'disconnect':
            connection.disconnect()
            return jsonify({
                "success": True,
                "status": "disconnected",
                "message": f"Connection {connection_name} disconnected"
            })
        elif action == 'configure':
            # Configuration already handled above
            return jsonify({
                "success": True,
                "status": "configured",
                "message": f"Connection {connection_name} configured successfully"
            })
        else:
            return jsonify({"error": f"Unknown action: {action}"}), 400
            
    except Exception as e:
        logger.error(f"Error in connection action: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
