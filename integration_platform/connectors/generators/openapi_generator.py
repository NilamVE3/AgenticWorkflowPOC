"""
OpenAPI-based Connector Generator - Auto-generate connectors from OpenAPI specs
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json
import yaml
import asyncio
import logging
from pydantic import BaseModel, Field
from connectors.sdk.base_connector import (
    BaseConnector, AuthenticationConfig, AuthenticationType,
    TriggerDefinition, ActionDefinition, TriggerType, ActionType
)

logger = logging.getLogger(__name__)

class OpenAPIEndpoint(BaseModel):
    """Representation of an OpenAPI endpoint"""
    path: str
    method: str
    operation_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[Dict[str, Any]] = []
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Any] = {}
    tags: List[str] = []

class OpenAPISpec(BaseModel):
    """Parsed OpenAPI specification"""
    openapi: str
    info: Dict[str, Any]
    servers: List[Dict[str, Any]] = []
    paths: Dict[str, Dict[str, OpenAPIEndpoint]] = {}
    components: Dict[str, Any] = {}

class GeneratedConnector(BaseConnector):
    """Auto-generated connector from OpenAPI spec"""
    
    def __init__(self, spec: OpenAPISpec, name: str = None):
        self.spec = spec
        self.base_url = spec.servers[0]["url"] if spec.servers else ""
        
        # Generate connector name from API info
        connector_name = name or spec.info.get("title", "API").replace(" ", "_").lower()
        super().__init__(connector_name)
        
        # Generate auth config
        self.auth_config = self._generate_auth_config()
        
        # Generate actions from endpoints
        self.actions = self._generate_actions()
        
        # Generate triggers from webhooks
        self.triggers = self._generate_triggers()
    
    def get_auth_config(self) -> AuthenticationConfig:
        """Generate authentication configuration"""
        return self.auth_config
    
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate with the API"""
        # Store credentials for use in requests
        self.credentials = credentials
        self.is_authenticated = True
        return True
    
    async def refresh_token(self) -> bool:
        """Refresh authentication token if needed"""
        # For OAuth2, implement token refresh logic
        if self.auth_config.auth_type == AuthenticationType.OAUTH2:
            # Implement OAuth2 token refresh
            pass
        return True
    
    def get_triggers(self) -> Dict[str, TriggerDefinition]:
        """Return available triggers"""
        return self.triggers
    
    def get_actions(self) -> Dict[str, ActionDefinition]:
        """Return available actions"""
        return self.actions
    
    async def execute_action(
        self,
        action_name: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute an API action"""
        action = self.actions.get(action_name)
        if not action:
            return {"success": False, "error": f"Action {action_name} not found"}
        
        # Build request URL
        url = self._build_url(action.input_schema.get("path", ""))
        
        # Prepare request data
        method = action.input_schema.get("method", "GET")
        headers = self._build_headers()
        params = {}
        body = None
        
        # Extract parameters from input_data
        for param_name, param_config in action.input_schema.get("parameters", {}).items():
            if param_name in input_data:
                param_location = param_config.get("in", "query")
                if param_location == "query":
                    params[param_name] = input_data[param_name]
                elif param_location == "header":
                    headers[param_name] = input_data[param_name]
                elif param_location == "path":
                    url = url.replace(f"{{{param_name}}}", str(input_data[param_name]))
        
        # Handle request body
        if method in ["POST", "PUT", "PATCH"]:
            body = input_data.get("body")
        
        # Make the API request
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=body
                ) as response:
                    result_data = await response.json() if response.content_type == "application/json" else await response.text()
                    
                    if response.status >= 400:
                        return {
                            "success": False,
                            "error": f"API request failed: {response.status}",
                            "response": result_data
                        }
                    
                    return {
                        "success": True,
                        "data": result_data,
                        "status": response.status
                    }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }
    
    async def setup_trigger(
        self,
        trigger_name: str,
        config: Dict[str, Any],
        webhook_url: str = None
    ) -> Dict[str, Any]:
        """Setup a webhook trigger"""
        trigger = self.triggers.get(trigger_name)
        if not trigger:
            return {"success": False, "error": f"Trigger {trigger_name} not found"}
        
        # For webhook triggers, register with external service
        if trigger.trigger_type == TriggerType.WEBHOOK and webhook_url:
            # Implement webhook registration logic
            return {"success": True, "trigger_id": str(uuid.uuid4())}
        
        return {"success": False, "error": "Trigger setup not implemented"}
    
    async def remove_trigger(self, trigger_id: str) -> bool:
        """Remove a trigger"""
        # Implement trigger removal logic
        return True
    
    def _generate_auth_config(self) -> AuthenticationConfig:
        """Generate authentication config from OpenAPI spec"""
        security_schemes = self.spec.components.get("securitySchemes", {})
        
        if not security_schemes:
            # Default to API key if no security defined
            return AuthenticationConfig(
                auth_type=AuthenticationType.API_KEY,
                required_fields=["api_key"],
                optional_fields=["header_name", "query_param"]
            )
        
        # Use first security scheme
        scheme_name = list(security_schemes.keys())[0]
        scheme = security_schemes[scheme_name]
        scheme_type = scheme.get("type", "").lower()
        
        if scheme_type == "oauth2":
            return AuthenticationConfig(
                auth_type=AuthenticationType.OAUTH2,
                required_fields=["client_id", "client_secret"],
                optional_fields=["scope", "redirect_uri"],
                token_refresh_config={"enabled": True}
            )
        elif scheme_type == "apikey":
            return AuthenticationConfig(
                auth_type=AuthenticationType.API_KEY,
                required_fields=["api_key"],
                optional_fields=["header_name", "query_param"]
            )
        elif scheme_type == "http":
            if scheme.get("scheme", "").lower() == "bearer":
                return AuthenticationConfig(
                    auth_type=AuthenticationType.BEARER_TOKEN,
                    required_fields=["token"]
                )
            else:
                return AuthenticationConfig(
                    auth_type=AuthenticationType.BASIC_AUTH,
                    required_fields=["username", "password"]
                )
        else:
            # Default to API key
            return AuthenticationConfig(
                auth_type=AuthenticationType.API_KEY,
                required_fields=["api_key"]
            )
    
    def _generate_actions(self) -> Dict[str, ActionDefinition]:
        """Generate actions from OpenAPI endpoints"""
        actions = {}
        
        for path, path_item in self.spec.paths.items():
            for method, endpoint in path_item.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    action_name = self._generate_action_name(endpoint, method, path)
                    
                    input_schema = {
                        "method": method.upper(),
                        "path": path,
                        "parameters": {}
                    }
                    
                    # Add parameters
                    for param in endpoint.parameters:
                        param_name = param["name"]
                        param_schema = {
                            "type": param.get("schema", {}).get("type", "string"),
                            "description": param.get("description", ""),
                            "in": param.get("in", "query"),
                            "required": param.get("required", False)
                        }
                        input_schema["parameters"][param_name] = param_schema
                    
                    # Add request body if present
                    if endpoint.request_body:
                        input_schema["body"] = endpoint.request_body
                    
                    # Determine action type
                    action_type = self._map_method_to_action(method)
                    
                    action = ActionDefinition(
                        name=action_name,
                        description=endpoint.summary or endpoint.description or f"{method.upper()} {path}",
                        action_type=action_type,
                        input_schema=input_schema,
                        output_schema=self._extract_response_schema(endpoint)
                    )
                    
                    actions[action_name] = action
        
        return actions
    
    def _generate_triggers(self) -> Dict[str, TriggerDefinition]:
        """Generate triggers from webhook endpoints"""
        triggers = {}
        
        # Look for webhook endpoints (typically POST endpoints that create resources)
        for path, path_item in self.spec.paths.items():
            if "post" in path_item:
                endpoint = path_item["post"]
                
                # Check if this might be a webhook endpoint
                if self._is_webhook_endpoint(endpoint, path):
                    trigger_name = f"webhook_{path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}"
                    
                    input_schema = {
                        "webhook_url": {"type": "string", "description": "URL to receive webhook events"}
                    }
                    
                    trigger = TriggerDefinition(
                        name=trigger_name,
                        description=f"Webhook trigger for {endpoint.summary or path}",
                        trigger_type=TriggerType.WEBHOOK,
                        input_schema=input_schema,
                        webhook_config={
                            "method": "POST",
                            "path": path
                        }
                    )
                    
                    triggers[trigger_name] = trigger
        
        return triggers
    
    def _generate_action_name(self, endpoint: OpenAPIEndpoint, method: str, path: str) -> str:
        """Generate a meaningful action name"""
        # Use operation_id if available
        if endpoint.operation_id:
            return endpoint.operation_id
        
        # Generate from method and path
        path_parts = [part for part in path.split("/") if part and not part.startswith("{")]
        method_prefix = method.lower()
        
        if path_parts:
            return f"{method_prefix}_{'_'.join(path_parts)}"
        else:
            return f"{method_prefix}_api"
    
    def _map_method_to_action(self, method: str) -> ActionType:
        """Map HTTP method to action type"""
        method = method.upper()
        if method == "GET":
            return ActionType.READ
        elif method == "POST":
            return ActionType.CREATE
        elif method == "PUT" or method == "PATCH":
            return ActionType.UPDATE
        elif method == "DELETE":
            return ActionType.DELETE
        else:
            return ActionType.CUSTOM
    
    def _extract_response_schema(self, endpoint: OpenAPIEndpoint) -> Dict[str, Any]:
        """Extract response schema from endpoint"""
        if not endpoint.responses:
            return {}
        
        # Use first successful response
        for status_code, response in endpoint.responses.items():
            if status_code.startswith("2"):
                content = response.get("content", {})
                if "application/json" in content:
                    return content["application/json"].get("schema", {})
        
        return {}
    
    def _is_webhook_endpoint(self, endpoint: OpenAPIEndpoint, path: str) -> bool:
        """Determine if an endpoint is likely a webhook"""
        # Heuristics for webhook detection
        webhook_indicators = [
            "webhook", "callback", "notification", "event",
            "incoming", "receive", "listen"
        ]
        
        # Check in path, summary, and description
        text_to_check = f"{path} {endpoint.summary or ''} {endpoint.description or ''}".lower()
        
        return any(indicator in text_to_check for indicator in webhook_indicators)
    
    def _build_url(self, path: str) -> str:
        """Build full URL from base URL and path"""
        if path.startswith("/"):
            return f"{self.base_url}{path}"
        else:
            return f"{self.base_url}/{path}"
    
    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with authentication"""
        headers = {"Content-Type": "application/json"}
        
        if not self.credentials:
            return headers
        
        auth_type = self.auth_config.auth_type
        
        if auth_type == AuthenticationType.API_KEY:
            api_key = self.credentials.get("api_key")
            if api_key:
                header_name = self.credentials.get("header_name", "X-API-Key")
                headers[header_name] = api_key
        
        elif auth_type == AuthenticationType.BEARER_TOKEN:
            token = self.credentials.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        
        elif auth_type == AuthenticationType.BASIC_AUTH:
            username = self.credentials.get("username")
            password = self.credentials.get("password")
            if username and password:
                import base64
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"
        
        elif auth_type == AuthenticationType.OAUTH2:
            access_token = self.credentials.get("access_token")
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
        
        return headers

class OpenAPIConnectorGenerator:
    """Generator for creating connectors from OpenAPI specifications"""
    
    def __init__(self):
        self.generated_connectors: Dict[str, type] = {}
    
    async def generate_from_url(self, spec_url: str, name: str = None) -> type:
        """Generate connector from OpenAPI spec URL"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(spec_url) as response:
                    if response.status == 200:
                        content_type = response.content_type
                        if "application/json" in content_type:
                            spec_data = await response.json()
                        else:
                            spec_text = await response.text()
                            spec_data = yaml.safe_load(spec_text)
                        
                        return self.generate_from_spec(spec_data, name)
                    else:
                        raise Exception(f"Failed to fetch spec: {response.status}")
        
        except Exception as e:
            logger.error(f"Failed to generate connector from URL: {str(e)}")
            raise
    
    def generate_from_spec(self, spec_data: Dict[str, Any], name: str = None) -> type:
        """Generate connector from OpenAPI spec data"""
        try:
            # Parse the OpenAPI spec
            spec = self._parse_spec(spec_data)
            
            # Create connector class
            class_name = name or spec.info.get("title", "GeneratedAPI").replace(" ", "")
            
            connector_class = type(
                class_name,
                (GeneratedConnector,),
                {"__init__": lambda self: GeneratedConnector.__init__(self, spec)}
            )
            
            # Store the generated class
            self.generated_connectors[class_name] = connector_class
            
            logger.info(f"Generated connector class: {class_name}")
            return connector_class
        
        except Exception as e:
            logger.error(f"Failed to generate connector from spec: {str(e)}")
            raise
    
    def _parse_spec(self, spec_data: Dict[str, Any]) -> OpenAPISpec:
        """Parse OpenAPI specification data"""
        # Convert OpenAPI 3.0 paths to our format
        paths = {}
        for path, path_item in spec_data.get("paths", {}).items():
            paths[path] = {}
            for method, operation in path_item.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    endpoint = OpenAPIEndpoint(
                        path=path,
                        method=method.upper(),
                        operation_id=operation.get("operationId"),
                        summary=operation.get("summary"),
                        description=operation.get("description"),
                        parameters=operation.get("parameters", []),
                        request_body=operation.get("requestBody"),
                        responses=operation.get("responses", {}),
                        tags=operation.get("tags", [])
                    )
                    paths[path][method] = endpoint
        
        return OpenAPISpec(
            openapi=spec_data.get("openapi", "3.0.0"),
            info=spec_data.get("info", {}),
            servers=spec_data.get("servers", []),
            paths=paths,
            components=spec_data.get("components", {})
        )
    
    def list_generated_connectors(self) -> List[str]:
        """List all generated connector classes"""
        return list(self.generated_connectors.keys())
    
    def get_connector_class(self, name: str) -> Optional[type]:
        """Get a generated connector class by name"""
        return self.generated_connectors.get(name)

class GenericRESTConnector(BaseConnector):
    """Generic REST connector for user-defined APIs"""
    
    def __init__(self, name: str = "generic_rest"):
        super().__init__(name)
        self.auth_config = AuthenticationConfig(
            auth_type=AuthenticationType.API_KEY,
            required_fields=["base_url"],
            optional_fields=["api_key", "username", "password", "token"]
        )
        
        # Generic actions for common REST operations
        self.actions = {
            "get_request": ActionDefinition(
                name="get_request",
                description="Make a GET request",
                action_type=ActionType.READ,
                input_schema={
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "API endpoint"},
                        "params": {"type": "object", "description": "Query parameters"}
                    },
                    "required": ["endpoint"]
                }
            ),
            "post_request": ActionDefinition(
                name="post_request",
                description="Make a POST request",
                action_type=ActionType.CREATE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "API endpoint"},
                        "body": {"type": "object", "description": "Request body"},
                        "params": {"type": "object", "description": "Query parameters"}
                    },
                    "required": ["endpoint"]
                }
            ),
            "put_request": ActionDefinition(
                name="put_request",
                description="Make a PUT request",
                action_type=ActionType.UPDATE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "API endpoint"},
                        "body": {"type": "object", "description": "Request body"}
                    },
                    "required": ["endpoint"]
                }
            ),
            "delete_request": ActionDefinition(
                name="delete_request",
                description="Make a DELETE request",
                action_type=ActionType.DELETE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "API endpoint"}
                    },
                    "required": ["endpoint"]
                }
            )
        }
    
    def get_auth_config(self) -> AuthenticationConfig:
        return self.auth_config
    
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        self.credentials = credentials
        self.is_authenticated = True
        return True
    
    async def refresh_token(self) -> bool:
        return True
    
    def get_triggers(self) -> Dict[str, TriggerDefinition]:
        return {}
    
    def get_actions(self) -> Dict[str, ActionDefinition]:
        return self.actions
    
    async def execute_action(
        self,
        action_name: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute a generic REST action"""
        base_url = self.credentials.get("base_url")
        if not base_url:
            return {"success": False, "error": "Base URL not configured"}
        
        endpoint = input_data.get("endpoint", "")
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        method = action_name.split("_")[0].upper()
        headers = self._build_headers()
        params = input_data.get("params", {})
        body = input_data.get("body")
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=body
                ) as response:
                    result_data = await response.json() if response.content_type == "application/json" else await response.text()
                    
                    if response.status >= 400:
                        return {
                            "success": False,
                            "error": f"Request failed: {response.status}",
                            "response": result_data
                        }
                    
                    return {
                        "success": True,
                        "data": result_data,
                        "status": response.status
                    }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }
    
    async def setup_trigger(
        self,
        trigger_name: str,
        config: Dict[str, Any],
        webhook_url: str = None
    ) -> Dict[str, Any]:
        return {"success": False, "error": "Triggers not supported"}
    
    async def remove_trigger(self, trigger_id: str) -> bool:
        return True
    
    def _build_headers(self) -> Dict[str, str]:
        """Build request headers"""
        headers = {"Content-Type": "application/json"}
        
        if self.credentials.get("api_key"):
            headers["X-API-Key"] = self.credentials["api_key"]
        
        if self.credentials.get("token"):
            headers["Authorization"] = f"Bearer {self.credentials['token']}"
        
        if self.credentials.get("username") and self.credentials.get("password"):
            import base64
            credentials = base64.b64encode(
                f"{self.credentials['username']}:{self.credentials['password']}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        return headers

# Global connector generator
connector_generator = OpenAPIConnectorGenerator()
