# Integration Platform API Documentation

## Overview

The Integration Platform provides a comprehensive REST API for managing connectors, workflows, tools, and executions. This API enables programmatic access to all platform features.

## Base URL

```
http://localhost:8000
```

## Authentication

All API endpoints (except authentication endpoints) require JWT authentication. Include token in Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

## API Endpoints

### Health & System

#### Health Check
```http
GET /health
```

#### System Information
```http
GET /api/system/info
```

### Authentication

#### Login
```http
POST /api/auth/login
```

**Request Body:**
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "jwt_token_here",
  "token_type": "Bearer",
  "user_id": "user123"
}
```

#### OAuth2 Initiation
```http
POST /api/auth/oauth2/initiate
```

#### OAuth2 Callback
```http
POST /api/auth/oauth2/callback
```

#### User Credentials
```http
GET /api/auth/credentials
```

### Tools Management

#### List Tools
```http
GET /api/tools
```

#### Get Tool Details
```http
GET /api/tools/{tool_id}
```

#### Execute Tool
```http
POST /api/tools/execute
```

**Request Body:**
```json
{
  "tool_id": "slack_send_message",
  "parameters": {
    "channel": "#general",
    "message": "Hello from API!"
  },
  "user_context": {
    "user_id": "user123"
  }
}
```

### Workflows Management

#### List Workflows
```http
GET /api/workflows
```

#### Create Workflow
```http
POST /api/workflows
```

**Request Body:**
```json
{
  "name": "My Workflow",
  "description": "Sample workflow",
  "steps": [
    {
      "id": "step1",
      "name": "Send Message",
      "type": "action",
      "config": {
        "tool_id": "slack_send_message",
        "parameters": {
          "channel": "#alerts",
          "message": "Workflow executed!"
        }
      }
    }
  ],
  "trigger": {
    "type": "webhook",
    "config": {
      "webhook_path": "my-webhook"
    }
  }
}
```

#### Get Workflow Details
```http
GET /api/workflows/{workflow_id}
```

#### Execute Workflow
```http
POST /api/workflows/{workflow_id}/execute
```

#### Get Workflow Executions
```http
GET /api/workflows/{workflow_id}/executions
```

#### Get Execution Status
```http
GET /api/executions/{execution_id}
```

### Triggers Management

#### List Triggers
```http
GET /api/triggers
```

#### Create Trigger
```http
POST /api/triggers
```

#### Get Webhook URL
```http
GET /api/triggers/{trigger_id}/webhook-url
```

### Connectors Management

#### List Connectors
```http
GET /api/connectors
```

#### Register Connector
```http
POST /api/connectors/register
```

**Request Body:**
```json
{
  "name": "my_api",
  "openapi_spec_url": "https://api.example.com/openapi.json",
  "auth_config": {
    "type": "api_key",
    "api_key_header": "X-API-Key"
  }
}
```

### Agent & AI Integration

#### Chat with Agent
```http
POST /api/agent/chat
```

**Request Body:**
```json
{
  "prompt": "Send a Slack message when a new user signs up",
  "capabilities": ["workflow_generation"],
  "available_tools": ["slack_send_message", "http_post_request"]
}
```

#### Generate Workflow from Prompt
```http
POST /api/agent/workflow
```

**Request Body:**
```json
{
  "prompt": "Create a workflow that monitors API and sends alerts",
  "user_context": {
    "user_id": "user123"
  }
}
```

### Task Management

#### Create Background Task
```http
POST /api/tasks
```

#### Get Task Status
```http
GET /api/tasks/{task_id}
```

### Webhooks

#### Handle Incoming Webhook
```http
POST /webhooks/{trigger_id}
```

### WebSocket

#### Real-time Updates
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Real-time update:', data);
};
```

## Error Responses

All endpoints return consistent error format:

```json
{
  "error": "Error message",
  "message": "Detailed error description",
  "timestamp": "2025-05-06T12:00:00Z"
}
```

## Rate Limiting

API endpoints are rate-limited to prevent abuse:
- Default: 100 requests per minute
- Authentication: 10 requests per minute

## SDK Examples

### Python SDK
```python
import requests

class IntegrationPlatformClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.token = None
    
    def login(self, username, password):
        response = requests.post(f"{self.base_url}/api/auth/login", {
            "username": username,
            "password": password
        })
        self.token = response.json()["access_token"]
        return self.token
    
    def execute_tool(self, tool_id, parameters):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.base_url}/api/tools/execute",
            headers=headers,
            json={
                "tool_id": tool_id,
                "parameters": parameters
            }
        )
        return response.json()

# Usage
client = IntegrationPlatformClient()
client.login("user", "password")
result = client.execute_tool("slack_send_message", {
    "channel": "#general",
    "message": "Hello from SDK!"
})
```

### JavaScript SDK
```javascript
class IntegrationPlatformClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.token = null;
    }
    
    async login(username, password) {
        const response = await fetch(`${this.baseUrl}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await response.json();
        this.token = data.access_token;
        return this.token;
    }
    
    async executeTool(toolId, parameters) {
        const response = await fetch(`${this.baseUrl}/api/tools/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`
            },
            body: JSON.stringify({
                tool_id: toolId,
                parameters: parameters
            })
        });
        return await response.json();
    }
}

// Usage
const client = new IntegrationPlatformClient();
await client.login('user', 'password');
const result = await client.executeTool('slack_send_message', {
    channel: '#general',
    message: 'Hello from SDK!'
});
```

## Support

For API support and questions:
- Documentation: [Integration Platform Docs](./README.md)
- API Reference: Available at `/docs` endpoint
- Issues: [GitHub Issues](https://github.com/your-org/integration-platform/issues)
