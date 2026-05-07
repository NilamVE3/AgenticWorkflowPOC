"""
HTTP Connector - Generic REST API connector
"""

from typing import Dict, Any, List, Optional
import asyncio
import logging
import json
from connectors.sdk.base_connector import (
    BaseConnector, AuthenticationConfig, AuthenticationType,
    TriggerDefinition, ActionDefinition, TriggerType, ActionType
)

logger = logging.getLogger(__name__)

class HTTPConnector(BaseConnector):
    """Generic HTTP/REST API connector"""
    
    def __init__(self):
        super().__init__("http", "1.0.0")
        
        # Set authentication configuration
        self.auth_config = AuthenticationConfig(
            auth_type=AuthenticationType.API_KEY,
            required_fields=["base_url"],
            optional_fields=["api_key", "username", "password", "bearer_token", "headers"],
            token_refresh_config={"enabled": False}
        )
        
        # Define actions
        self.actions = {
            "get_request": ActionDefinition(
                name="get_request",
                description="Make a GET request to an API endpoint",
                action_type=ActionType.READ,
                input_schema={
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "API endpoint path"},
                        "params": {"type": "object", "description": "Query parameters"},
                        "headers": {"type": "object", "description": "Additional headers"}
                    },
                    "required": ["endpoint"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status_code": {"type": "integer"},
                        "response_body": {"type": "object"},
                        "headers": {"type": "object"}
                    }
                }
            ),
            "post_request": ActionDefinition(
                name="post_request",
                description="Make a POST request to an API endpoint",
                action_type=ActionType.CREATE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "API endpoint path"},
                        "body": {"type": "object", "description": "Request body"},
                        "params": {"type": "object", "description": "Query parameters"},
                        "headers": {"type": "object", "description": "Additional headers"}
                    },
                    "required": ["endpoint"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status_code": {"type": "integer"},
                        "response_body": {"type": "object"},
                        "headers": {"type": "object"}
                    }
                }
            ),
            "put_request": ActionDefinition(
                name="put_request",
                description="Make a PUT request to an API endpoint",
                action_type=ActionType.UPDATE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "API endpoint path"},
                        "body": {"type": "object", "description": "Request body"},
                        "params": {"type": "object", "description": "Query parameters"},
                        "headers": {"type": "object", "description": "Additional headers"}
                    },
                    "required": ["endpoint"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status_code": {"type": "integer"},
                        "response_body": {"type": "object"},
                        "headers": {"type": "object"}
                    }
                }
            ),
            "delete_request": ActionDefinition(
                name="delete_request",
                description="Make a DELETE request to an API endpoint",
                action_type=ActionType.DELETE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "API endpoint path"},
                        "params": {"type": "object", "description": "Query parameters"},
                        "headers": {"type": "object", "description": "Additional headers"}
                    },
                    "required": ["endpoint"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status_code": {"type": "integer"},
                        "response_body": {"type": "object"},
                        "headers": {"type": "object"}
                    }
                }
            ),
            "patch_request": ActionDefinition(
                name="patch_request",
                description="Make a PATCH request to an API endpoint",
                action_type=ActionType.UPDATE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "API endpoint path"},
                        "body": {"type": "object", "description": "Request body"},
                        "params": {"type": "object", "description": "Query parameters"},
                        "headers": {"type": "object", "description": "Additional headers"}
                    },
                    "required": ["endpoint"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status_code": {"type": "integer"},
                        "response_body": {"type": "object"},
                        "headers": {"type": "object"}
                    }
                }
            )
        }
        
        # Define triggers
        self.triggers = {
            "webhook_receiver": TriggerDefinition(
                name="webhook_receiver",
                description="Receive webhook events from external services",
                trigger_type=TriggerType.WEBHOOK,
                input_schema={
                    "type": "object",
                    "properties": {
                        "webhook_path": {"type": "string", "description": "Webhook path"},
                        "secret": {"type": "string", "description": "Optional secret for signature verification"}
                    },
                    "required": ["webhook_path"]
                },
                webhook_config={
                    "method": "POST",
                    "signature_header": "X-Signature"
                }
            ),
            "polling_trigger": TriggerDefinition(
                name="polling_trigger",
                description="Poll an API endpoint for changes",
                trigger_type=TriggerType.POLLING,
                input_schema={
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "API endpoint to poll"},
                        "interval": {"type": "integer", "description": "Polling interval in seconds"},
                        "method": {"type": "string", "description": "HTTP method", "enum": ["GET", "POST"]},
                        "params": {"type": "object", "description": "Query parameters"},
                        "headers": {"type": "object", "description": "Headers"},
                        "body": {"type": "object", "description": "Request body for POST"}
                    },
                    "required": ["endpoint", "interval"]
                },
                polling_config={
                    "default_interval": 60,
                    "max_interval": 3600
                }
            )
        }
    
    def get_auth_config(self) -> AuthenticationConfig:
        return self.auth_config
    
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate with HTTP service"""
        self.credentials = credentials
        self.base_url = credentials.get("base_url")
        
        if not self.base_url:
            return False
        
        # Test connection with a simple request
        try:
            headers = self._build_headers()
            async with self._get_session() as session:
                async with session.get(f"{self.base_url}/", headers=headers) as response:
                    # Accept any response as long as we can connect
                    self.is_authenticated = True
                    return True
        except Exception as e:
            logger.error(f"HTTP authentication failed: {str(e)}")
            return False
    
    async def refresh_token(self) -> bool:
        """HTTP connectors typically don't need token refresh"""
        return True
    
    def get_triggers(self) -> Dict[str, TriggerDefinition]:
        return self.triggers
    
    def get_actions(self) -> Dict[str, ActionDefinition]:
        return self.actions
    
    async def execute_action(
        self,
        action_name: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute an HTTP action"""
        if not self.is_authenticated:
            return {"success": False, "error": "Not authenticated"}
        
        try:
            if action_name == "get_request":
                return await self._make_request("GET", input_data)
            elif action_name == "post_request":
                return await self._make_request("POST", input_data)
            elif action_name == "put_request":
                return await self._make_request("PUT", input_data)
            elif action_name == "delete_request":
                return await self._make_request("DELETE", input_data)
            elif action_name == "patch_request":
                return await self._make_request("PATCH", input_data)
            else:
                return {"success": False, "error": f"Unknown action: {action_name}"}
        
        except Exception as e:
            logger.error(f"HTTP action {action_name} failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def setup_trigger(
        self,
        trigger_name: str,
        config: Dict[str, Any],
        webhook_url: str = None
    ) -> Dict[str, Any]:
        """Setup an HTTP trigger"""
        if trigger_name == "webhook_receiver":
            return await self._setup_webhook_trigger(config, webhook_url)
        elif trigger_name == "polling_trigger":
            return await self._setup_polling_trigger(config)
        else:
            return {"success": False, "error": f"Unknown trigger: {trigger_name}"}
    
    async def remove_trigger(self, trigger_id: str) -> bool:
        """Remove an HTTP trigger"""
        # For HTTP connectors, triggers are typically managed externally
        return True
    
    async def _make_request(self, method: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make an HTTP request"""
        import aiohttp
        
        endpoint = input_data.get("endpoint", "")
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]
        
        url = f"{self.base_url.rstrip('/')}/{endpoint}"
        headers = self._build_headers()
        
        # Add custom headers
        if "headers" in input_data:
            headers.update(input_data["headers"])
        
        params = input_data.get("params", {})
        body = input_data.get("body")
        
        # Set default content type for requests with body
        if body and method in ["POST", "PUT", "PATCH"] and "content-type" not in headers:
            headers["content-type"] = "application/json"
        
        try:
            async with self._get_session() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=body if headers.get("content-type") == "application/json" else None,
                    data=body if headers.get("content-type") != "application/json" else None
                ) as response:
                    # Parse response
                    response_headers = dict(response.headers)
                    
                    try:
                        if response.content_type and "json" in response.content_type:
                            response_body = await response.json()
                        else:
                            response_body = await response.text()
                    except:
                        response_body = await response.text()
                    
                    return {
                        "success": True,
                        "data": {
                            "status_code": response.status,
                            "response_body": response_body,
                            "headers": response_headers
                        }
                    }
        
        except aiohttp.ClientError as e:
            return {
                "success": False,
                "error": f"HTTP request failed: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }
    
    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with authentication"""
        headers = {}
        
        # Add authentication headers
        if "api_key" in self.credentials:
            api_key = self.credentials["api_key"]
            header_name = self.credentials.get("api_key_header", "X-API-Key")
            headers[header_name] = api_key
        
        if "bearer_token" in self.credentials:
            headers["Authorization"] = f"Bearer {self.credentials['bearer_token']}"
        
        if "username" in self.credentials and "password" in self.credentials:
            import base64
            credentials = base64.b64encode(
                f"{self.credentials['username']}:{self.credentials['password']}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        # Add custom headers
        if "headers" in self.credentials:
            headers.update(self.credentials["headers"])
        
        return headers
    
    def _get_session(self):
        """Get aiohttp session with appropriate configuration"""
        import aiohttp
        
        # Configure timeout and connection limits
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
        
        return aiohttp.ClientSession(timeout=timeout, connector=connector)
    
    async def _setup_webhook_trigger(self, config: Dict[str, Any], webhook_url: str) -> Dict[str, Any]:
        """Setup webhook trigger"""
        # For HTTP connectors, webhook setup is typically done by the external service
        # We just return the webhook URL that should be configured in the external service
        
        webhook_path = config.get("webhook_path", "")
        if webhook_path.startswith("/"):
            webhook_path = webhook_path[1:]
        
        full_webhook_url = f"{webhook_url.rstrip('/')}/{webhook_path}"
        
        return {
            "success": True,
            "trigger_id": f"webhook_{hash(full_webhook_url)}",
            "webhook_url": full_webhook_url,
            "message": "Webhook trigger setup successful. Configure this URL in the external service."
        }
    
    async def _setup_polling_trigger(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Setup polling trigger"""
        # For polling triggers, we just validate the configuration
        endpoint = config.get("endpoint")
        interval = config.get("interval", 60)
        
        if not endpoint:
            return {"success": False, "error": "Endpoint is required"}
        
        if interval < 10:
            return {"success": False, "error": "Interval must be at least 10 seconds"}
        
        return {
            "success": True,
            "trigger_id": f"polling_{hash(endpoint)}_{interval}",
            "message": "Polling trigger setup successful"
        }
    
    async def handle_webhook(self, trigger_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming webhook data"""
        # Process webhook data
        processed_data = {
            "trigger_id": trigger_id,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        return {"processed": True, "data": processed_data}
    
    async def poll_trigger(self, trigger_id: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Poll for trigger events"""
        try:
            # Make polling request
            method = config.get("method", "GET")
            input_data = {
                "endpoint": config.get("endpoint", ""),
                "params": config.get("params", {}),
                "headers": config.get("headers", {})
            }
            
            if method == "POST":
                input_data["body"] = config.get("body", {})
            
            result = await self._make_request(method, input_data)
            
            if result["success"]:
                response_data = result["data"]["response_body"]
                
                # Return as list of events
                if isinstance(response_data, list):
                    return response_data
                else:
                    return [response_data]
            else:
                logger.error(f"Polling trigger {trigger_id} failed: {result.get('error')}")
                return []
        
        except Exception as e:
            logger.error(f"Polling trigger {trigger_id} error: {str(e)}")
            return []

# Register the connector
from connectors.sdk.base_connector import connector_registry
connector_registry.register(HTTPConnector)
