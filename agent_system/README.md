# Agent System

A modular, extensible agent system for executing tasks with various tools and real-time connections.

## Structure

```
agent_system/
│
├── agent.py              # Core agent classes and execution engine
├── tool_registry.py      # Tool registration and management
├── schemas.py           # Data models and schemas
├── main.py              # Main entry point and CLI
├── requirements.txt     # Python dependencies
├── README.md           # This file
│
├── connectors/         # Real-time connection implementations
│   ├── slack.py        # Slack connector
│   ├── gmail.py        # Gmail connector
│   ├── weather.py      # Weather API connector
│   ├── websocket.py    # WebSocket connector
│   └── redis.py        # Redis connector
│
├── tools/              # Tool implementations
│   ├── slack_tools.py  # Slack tools
│   ├── gmail_tools.py  # Gmail tools
│   ├── weather_tools.py # Weather tools
│   ├── file_tools.py   # File operation tools
│   ├── api_tools.py    # HTTP API tools
│   └── database_tools.py # Database tools
│
└── __init__.py         # Package initialization
```

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Basic Usage

```python
from agent_system import AgentSystem

# Create and initialize the agent system
agent = AgentSystem()
agent.initialize()

# Execute a task
task_id = agent.execute_task(
    tool="file_operations",
    parameters={
        "action": "read",
        "filename": "example.txt"
    }
)

# Check task status
status = agent.get_task_status(task_id)
print(status)
```

### Command Line Interface

```bash
python main.py
```

Available commands in interactive mode:
- `list_tools` - List all available tools
- `list_connections` - List all connections
- `execute <tool> [json_params]` - Execute a tool
- `status <task_id>` - Get task status
- `quit` - Exit system

## Environment Variables

Configure integrations using environment variables:

```bash
# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_USER_TOKEN=xoxp-your-user-token

# Gmail
GMAIL_CLIENT_ID=your-client-id
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_ACCESS_TOKEN=your-access-token
GMAIL_REFRESH_TOKEN=your-refresh-token

# Weather
WEATHER_API_KEY=your-weather-api-key

# Redis (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Architecture

### Core Components

1. **AgentTool**: Base class for all tools
2. **RealTimeConnection**: Base class for real-time connections
3. **AgentExecutionEngine**: Core execution engine
4. **ToolRegistry**: Manages tool registration and discovery

### Tools

Tools implement the `AgentTool` interface and provide specific functionality:
- File operations
- HTTP API calls
- Database operations
- Slack integration
- Gmail integration
- Weather data

### Connectors

Connectors implement the `RealTimeConnection` interface for real-time data:
- WebSocket connections
- Redis pub/sub
- Slack real-time events
- Gmail monitoring
- Weather updates

## Adding New Tools

1. Create a new file in `tools/` directory
2. Inherit from `AgentTool`
3. Implement the `execute` method
4. Tool will be auto-registered when the system starts

Example:

```python
from agent_system import AgentTool

class MyTool(AgentTool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="My custom tool",
            parameters={
                "param1": {"type": "string", "description": "First parameter"}
            }
        )
        
    def execute(self, **kwargs):
        param1 = kwargs.get('param1')
        return {"success": True, "result": f"Processed: {param1}"}
```

## Adding New Connectors

1. Create a new file in `connectors/` directory
2. Inherit from `RealTimeConnection`
3. Implement connection methods
4. Connector will be auto-registered

Example:

```python
from agent_system import RealTimeConnection

class MyConnection(RealTimeConnection):
    def __init__(self):
        super().__init__("my_connection", "My Service")
        
    def connect(self):
        # Implement connection logic
        self.is_connected = True
        return True
        
    def disconnect(self):
        self.is_connected = False
        
    def send_data(self, data):
        # Implement data sending
        return True
        
    def receive_data(self):
        # Implement data receiving
        return {"data": "received"}
```

## License

MIT License
