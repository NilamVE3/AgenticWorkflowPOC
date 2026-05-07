# Integration Platform

A scalable, production-ready integration platform similar to Zapier that supports 1000+ connectors and agentic workflows.

## 🎯 Overview

This platform provides a complete solution for building integrations between various services and APIs with the following key features:

- **1000+ Connector Support**: Extensible connector framework with OpenAPI-based generation
- **Agentic Workflows**: AI-powered workflow generation and execution
- **Real-time Triggers**: Webhooks, polling, and scheduled triggers
- **Durable Execution**: Queue-based orchestration with retries and error handling
- **Multi-tenant Architecture**: Secure credential management and user isolation
- **RESTful API**: Complete API for external integrations
- **Modern UI**: Web dashboard for workflow management

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    API Gateway Layer                            │
├─────────────────────────────────────────────────────────────────┤
│                    Web UI Dashboard                             │
├─────────────────────────────────────────────────────────────────┤
│                    Agentic Layer (LLM)                         │
├─────────────────────────────────────────────────────────────────┤
│                    Workflow Engine                              │
├─────────────────────────────────────────────────────────────────┤
│                    Orchestration Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Task Queue  │  │ Workers     │  │ State Store │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
├─────────────────────────────────────────────────────────────────┤
│                    Tool Execution Layer                         │
├─────────────────────────────────────────────────────────────────┤
│                    Tool Registry                                │
├─────────────────────────────────────────────────────────────────┤
│                    Connector Framework                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Connectors  │  │ Auth        │  │ Triggers    │              │
│  │ (1000+)     │  │ Service     │  │ System      │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
├─────────────────────────────────────────────────────────────────┤
│                    Infrastructure                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Database    │  │ Cache       │  │ Message     │              │
│  │ (Postgres)  │  │ (Redis)     │  │ Broker      │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Redis (for task queues and caching)
- PostgreSQL (for persistent storage)

### Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd integration_platform
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Start required services**:
```bash
# Start Redis
redis-server

# Start PostgreSQL
# See your system documentation for PostgreSQL setup
```

5. **Initialize the database**:
```bash
python -m core.database.init_db
```

6. **Start the platform**:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## 📚 Core Components

### 1. Connector Framework

The connector framework provides a standardized interface for integrating with external services:

```python
from connectors.sdk.base_connector import BaseConnector

class MyConnector(BaseConnector):
    def __init__(self):
        super().__init__("my_service")
        
    async def authenticate(self, credentials):
        # Implement authentication
        pass
        
    async def execute_action(self, action_name, input_data, context):
        # Implement action execution
        pass
```

### 2. Tool Registry

Central registry for managing all available tools/actions:

```python
from tools.registry.tool_registry import tool_registry, ToolDefinition

# Register a tool
tool_def = ToolDefinition(
    name="my_tool",
    description="My custom tool",
    connector_name="my_connector",
    connector_action="perform_action",
    input_schema={"type": "object", "properties": {...}}
)

tool_registry.register_tool(tool_def)
```

### 3. Workflow Engine

JSON-based workflow execution with DAG support:

```json
{
  "name": "My Workflow",
  "steps": [
    {
      "id": "step1",
      "name": "First Step",
      "type": "action",
      "config": {
        "tool_id": "my_tool",
        "parameters": {...}
      }
    },
    {
      "id": "step2",
      "name": "Second Step",
      "type": "action",
      "config": {
        "tool_id": "another_tool",
        "parameters": {...}
      },
      "depends_on": ["step1"]
    }
  ]
}
```

### 4. Agentic Layer

AI-powered workflow generation and tool selection:

```python
from agents.llm.agentic_layer import agentic_layer, AgentRequest

# Generate workflow from prompt
request = AgentRequest(
    user_id="user123",
    prompt="Send a Slack message when a new user signs up",
    capabilities=["workflow_generation"]
)

response = await agentic_layer.process_request(request)
```

## 🔌 Connectors

### Built-in Connectors

- **Slack**: Messaging, channel management, file uploads
- **HTTP/REST**: Generic REST API connector
- **Email**: SMTP email sending
- **Database**: SQL database operations
- **Webhook**: Generic webhook receiver

### Adding New Connectors

1. **Create connector class**:
```python
class MyConnector(BaseConnector):
    # Implement required methods
    pass
```

2. **Register connector**:
```python
from connectors.sdk.base_connector import connector_registry
connector_registry.register(MyConnector)
```

3. **Generate from OpenAPI**:
```python
from connectors.generators.openapi_generator import connector_generator

connector_class = await connector_generator.generate_from_url(
    "https://api.example.com/openapi.json"
)
```

## 🔄 Workflows

### Creating Workflows

1. **Via API**:
```bash
curl -X POST http://localhost:8000/api/workflows \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "My Workflow",
    "steps": [...]
  }'
```

2. **Via AI Generation**:
```bash
curl -X POST http://localhost:8000/api/agent/workflow \
  -H "Authorization: Bearer <token>" \
  -d '{
    "prompt": "Send Slack notification when API event occurs"
  }'
```

### Sample Workflows

See `examples/sample_workflows.json` for example workflows including:
- Slack notifications on API events
- Daily report generation
- Customer onboarding
- Error monitoring and alerting
- Social media scheduling
- Data backup and verification

## 🔐 Authentication

### Supported Auth Types

- **OAuth2**: Full OAuth2 flow with token refresh
- **API Key**: Simple API key authentication
- **Basic Auth**: Username/password authentication
- **Bearer Token**: JWT or other bearer tokens

### Managing Credentials

```bash
# Store credentials
curl -X POST http://localhost:8000/api/auth/credentials \
  -H "Authorization: Bearer <token>" \
  -d '{
    "connector_name": "slack",
    "auth_type": "bearer_token",
    "credentials": {"token": "xoxb-..."}
  }'

# List credentials
curl -X GET http://localhost:8000/api/auth/credentials \
  -H "Authorization: Bearer <token>"
```

## 🎯 Triggers

### Trigger Types

1. **Webhooks**: Real-time event reception
2. **Polling**: Periodic API checking
3. **Scheduled**: Cron-based execution
4. **Manual**: Manual triggering

### Setting up Webhooks

```bash
# Create webhook trigger
curl -X POST http://localhost:8000/api/triggers \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "My Webhook",
    "type": "webhook",
    "connector_name": "slack",
    "config": {
      "webhook_path": "my-webhook"
    }
  }'

# Get webhook URL
curl -X GET http://localhost:8000/api/triggers/{trigger_id}/webhook-url \
  -H "Authorization: Bearer <token>"
```

## 📊 API Reference

### Core Endpoints

- `GET /api/tools` - List available tools
- `POST /api/tools/execute` - Execute a tool
- `GET /api/workflows` - List workflows
- `POST /api/workflows` - Create workflow
- `POST /api/workflows/{id}/execute` - Execute workflow
- `GET /api/triggers` - List triggers
- `POST /api/triggers` - Create trigger
- `POST /api/agent/chat` - Chat with AI agent
- `POST /api/agent/workflow` - Generate workflow from prompt

### Authentication

All API endpoints require JWT authentication:

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -d '{
    "username": "user@example.com",
    "password": "password"
  }'

# Use token in subsequent requests
curl -X GET http://localhost:8000/api/tools \
  -H "Authorization: Bearer <jwt_token>"
```

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/integration_platform

# Redis
REDIS_URL=redis://localhost:6379

# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Security
JWT_SECRET=your-jwt-secret
ENCRYPTION_KEY=your-encryption-key

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

### Scaling Configuration

```python
# Number of worker processes
NUM_WORKERS=10

# Task queue configuration
QUEUE_MAX_SIZE=10000
QUEUE_RETRY_ATTEMPTS=3

# Connection pools
DB_POOL_SIZE=20
REDIS_POOL_SIZE=10
```

## 🚀 Deployment

### Docker Deployment

```bash
# Build image
docker build -t integration-platform .

# Run with docker-compose
docker-compose up -d
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: integration-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: integration-platform
  template:
    metadata:
      labels:
        app: integration-platform
    spec:
      containers:
      - name: api
        image: integration-platform:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

## 📈 Monitoring

### Health Checks

- `GET /health` - Basic health check
- `GET /api/system/info` - System statistics

### Metrics

The platform exposes metrics for:
- Tool execution counts and success rates
- Workflow execution statistics
- Queue sizes and processing times
- Connector health status
- API request rates and response times

### Logging

Structured logging with the following levels:
- `ERROR`: Critical errors and failures
- `WARNING`: Recoverable issues and retries
- `INFO`: Normal operation and important events
- `DEBUG`: Detailed debugging information

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_connectors.py

# Run with coverage
python -m pytest --cov=integration_platform tests/
```

### Integration Tests

```bash
# Run integration tests
python -m pytest tests/integration/

# Test with real services
python -m pytest tests/integration/ --env=test
```

### Load Testing

```bash
# Run load tests
python -m pytest tests/load/ --workers=10
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Run linting
flake8 integration_platform/
black integration_platform/

# Run type checking
mypy integration_platform/
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: [Full documentation](https://docs.integration-platform.com)
- **Issues**: [GitHub Issues](https://github.com/your-org/integration-platform/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/integration-platform/discussions)
- **Community**: [Slack Community](https://integration-platform.slack.com)

## 🗺️ Roadmap

### Version 2.0
- [ ] Visual workflow builder
- [ ] Advanced error handling
- [ ] Multi-region deployment
- [ ] Advanced analytics dashboard

### Version 2.1
- [ ] GraphQL API support
- [ ] Advanced scheduling
- [ ] Custom function support
- [ ] Enhanced security features

### Version 3.0
- [ ] Event sourcing architecture
- [ ] Machine learning optimizations
- [ ] Advanced monitoring
- [ ] Enterprise features

---

**Built with ❤️ for the integration community**
