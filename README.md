# Agent-Driven Execution POC

A comprehensive Flask-based proof-of-concept for agent-driven execution with real-time tools and connections, inspired by platforms like Replit's 100+ real-time connections.

## Features

### 🔥 Core Capabilities
- **Agent-Driven Execution**: Core engine for executing tasks through various tools
- **Real-time Communication**: WebSocket-based real-time updates and notifications
- **Modular Tool System**: Extensible framework for adding custom tools
- **Connection Management**: Support for various real-time connections (WebSocket, Redis, etc.)
- **Task Management**: Asynchronous task execution with status tracking
- **Live Dashboard**: Interactive web interface for monitoring and control

### 🛠️ Built-in Tools
1. **File Operations Tool**: Read, write, delete files
2. **API Call Tool**: Make HTTP requests to external APIs
3. **Database Tool**: Perform database operations (mock implementation)

### 🌍 Real-World Integrations
1. **Gmail Integration**: Send, read, search, and manage emails
2. **Slack Integration**: Send messages, manage channels, upload files
3. **GitHub Integration**: Repository management, issues, pull requests
4. **Microsoft Teams**: Send messages, manage teams, create meetings
5. **Microsoft Outlook**: Email, calendar, and contact management

### 🔗 Real-time Connections
1. **WebSocket Connection**: Real-time bidirectional communication
2. **Redis Connection**: Caching and pub/sub capabilities

## Quick Start

### Installation
```bash
# Clone or navigate to the project directory
cd agentic_workflow

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API credentials
```

### Setting Up Integrations
```bash
# Run the setup wizard for OAuth integrations
python setup_integrations.py

# Test your integrations
python test_integrations.py
```

### Running the Application
```bash
python app.py
```

The application will start on `http://localhost:5000`

## Architecture

### Core Components

#### 1. AgentTool (Base Class)
```python
class AgentTool:
    def __init__(self, name: str, description: str, parameters: Dict[str, Any])
    def execute(self, **kwargs) -> Dict[str, Any]
```

#### 2. RealTimeConnection (Base Class)
```python
class RealTimeConnection:
    def __init__(self, name: str, connection_type: str)
    def connect(self) -> bool
    def disconnect(self)
    def send_data(self, data: Any) -> bool
    def receive_data(self) -> Any
```

#### 3. AgentExecutionEngine
- Task management and execution
- Tool and connection registry
- Real-time progress tracking
- Asynchronous execution with threading

### API Endpoints

#### Tools
- `GET /api/tools` - List all available tools
- `POST /api/tasks` - Create and execute a new task
- `GET /api/tasks` - Get all tasks (active and completed)
- `GET /api/tasks/<task_id>` - Get specific task status

#### WebSocket Events
- `execute_tool` - Execute tool directly via WebSocket
- `connection_action` - Manage connections (connect/disconnect)
- `task_update` - Real-time task status updates
- `tool_progress` - Tool execution progress

## Creating Custom Tools

Create a new tool by extending the `AgentTool` base class:

```python
class CustomTool(AgentTool):
    def __init__(self):
        super().__init__(
            name="custom_tool",
            description="Description of your custom tool",
            parameters={
                "param1": {"type": "string", "description": "Parameter description"},
                "param2": {"type": "integer", "description": "Another parameter"}
            }
        )
        self.is_realtime = True  # Set to True for real-time tools
        
    def execute(self, **kwargs) -> Dict[str, Any]:
        # Implement your tool logic here
        param1 = kwargs.get('param1')
        param2 = kwargs.get('param2')
        
        # Your tool implementation
        result = {"success": True, "data": "Tool executed successfully"}
        
        return result

# Register the tool
engine.register_tool(CustomTool())
```

## Creating Custom Connections

Create a new connection by extending the `RealTimeConnection` base class:

```python
class CustomConnection(RealTimeConnection):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("custom_connection", "Custom")
        self.config = config
        
    def connect(self) -> bool:
        try:
            # Implement connection logic
            self.is_connected = True
            return True
        except Exception as e:
            return False
            
    def disconnect(self):
        self.is_connected = False
        
    def send_data(self, data: Any) -> bool:
        if not self.is_connected:
            return False
        # Implement send logic
        return True
        
    def receive_data(self) -> Any:
        # Implement receive logic
        return {"data": "received"}

# Register the connection
engine.register_connection(CustomConnection(config))
```

## Web Interface

The dashboard provides:
- **Tools Panel**: View available tools and their parameters
- **Connections Panel**: Manage real-time connections
- **Task Creation**: Create and execute tasks through the UI
- **Active Tasks**: Monitor task execution in real-time
- **Live Logs**: Real-time system logs and updates

## Example Usage

### 1. File Operations
```json
{
    "tool": "file_operations",
    "description": "Read a configuration file",
    "parameters": {
        "action": "read",
        "filename": "config.json"
    }
}
```

### 2. API Calls
```json
{
    "tool": "api_call",
    "description": "Fetch user data from API",
    "parameters": {
        "url": "https://api.example.com/users/1",
        "method": "GET",
        "headers": {"Authorization": "Bearer token"}
    }
}
```

### 3. Database Operations
```json
{
    "tool": "database",
    "description": "Query user records",
    "parameters": {
        "operation": "select",
        "query": "SELECT * FROM users WHERE active = 1"
    }
}
```

## Scaling to 100+ Connections

The architecture is designed to scale:

1. **Modular Design**: Each connection is independent
2. **Async Execution**: Non-blocking task execution
3. **Connection Pooling**: Efficient resource management
4. **Real-time Updates**: WebSocket-based notifications
5. **Health Monitoring**: Connection status tracking

To add more connections:
1. Create connection classes extending `RealTimeConnection`
2. Register them with the engine
3. Add UI controls for management
4. Implement connection-specific logic

## Technology Stack

- **Backend**: Flask + Flask-SocketIO
- **Real-time**: WebSockets (Socket.IO)
- **Frontend**: HTML5 + JavaScript + CSS3
- **Async**: Python threading
- **Communication**: JSON over HTTP/WebSocket

## Development

### Adding New Features
1. Create tools/connections in separate files
2. Import and register in `app.py`
3. Add UI components if needed
4. Update API documentation

### Testing
```bash
# Test the API endpoints
curl http://localhost:5000/api/tools
curl http://localhost:5000/api/connections

# Test task execution
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"tool": "file_operations", "description": "Test file read", "parameters": {"action": "read", "filename": "test.txt"}}'
```

## Production Considerations

- Add authentication and authorization
- Implement rate limiting
- Add persistent storage for tasks
- Set up proper logging and monitoring
- Configure production-ready WebSocket server
- Add error handling and recovery mechanisms

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add your tools/connections
4. Update documentation
5. Submit a pull request

## License

MIT License - feel free to use and modify for your projects.
