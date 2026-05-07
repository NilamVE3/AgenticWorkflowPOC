"""
Base Connector SDK - Standard interface for all connectors
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

class AuthenticationType(str, Enum):
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC_AUTH = "basic_auth"
    BEARER_TOKEN = "bearer_token"
    CUSTOM = "custom"

class TriggerType(str, Enum):
    WEBHOOK = "webhook"
    POLLING = "polling"
    STREAMING = "streaming"
    SCHEDULED = "scheduled"

class ActionType(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    CUSTOM = "custom"

class AuthenticationConfig:
    """Configuration for connector authentication"""
    def __init__(
        self,
        auth_type: AuthenticationType,
        required_fields: List[str],
        optional_fields: List[str] = None,
        token_refresh_config: Dict[str, Any] = None
    ):
        self.auth_type = auth_type
        self.required_fields = required_fields
        self.optional_fields = optional_fields or []
        self.token_refresh_config = token_refresh_config or {}

class TriggerDefinition:
    """Definition for a trigger"""
    def __init__(
        self,
        name: str,
        description: str,
        trigger_type: TriggerType,
        input_schema: Dict[str, Any],
        webhook_config: Dict[str, Any] = None,
        polling_config: Dict[str, Any] = None
    ):
        self.name = name
        self.description = description
        self.trigger_type = trigger_type
        self.input_schema = input_schema
        self.webhook_config = webhook_config or {}
        self.polling_config = polling_config or {}

class ActionDefinition:
    """Definition for an action/tool"""
    def __init__(
        self,
        name: str,
        description: str,
        action_type: ActionType,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any] = None,
        rate_limit: Dict[str, Any] = None
    ):
        self.name = name
        self.description = description
        self.action_type = action_type
        self.input_schema = input_schema
        self.output_schema = output_schema or {}
        self.rate_limit = rate_limit or {}

class BaseConnector(ABC):
    """Base class for all connectors"""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.auth_config: Optional[AuthenticationConfig] = None
        self.triggers: Dict[str, TriggerDefinition] = {}
        self.actions: Dict[str, ActionDefinition] = {}
        self.credentials: Dict[str, Any] = {}
        self.is_authenticated = False
        self.metadata = {
            "created_at": datetime.now().isoformat(),
            "category": "general",
            "tags": []
        }
    
    @abstractmethod
    def get_auth_config(self) -> AuthenticationConfig:
        """Return the authentication configuration for this connector"""
        pass
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with the external service
        
        Args:
            credentials: Authentication credentials
            
        Returns:
            True if authentication successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def refresh_token(self) -> bool:
        """
        Refresh authentication token if needed
        
        Returns:
            True if refresh successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_triggers(self) -> Dict[str, TriggerDefinition]:
        """Return all available triggers for this connector"""
        pass
    
    @abstractmethod
    def get_actions(self) -> Dict[str, ActionDefinition]:
        """Return all available actions for this connector"""
        pass
    
    @abstractmethod
    async def execute_action(
        self,
        action_name: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute an action
        
        Args:
            action_name: Name of the action to execute
            input_data: Input data for the action
            context: Execution context (user_id, workflow_id, etc.)
            
        Returns:
            Result of the action execution
        """
        pass
    
    @abstractmethod
    async def setup_trigger(
        self,
        trigger_name: str,
        config: Dict[str, Any],
        webhook_url: str = None
    ) -> Dict[str, Any]:
        """
        Setup a trigger
        
        Args:
            trigger_name: Name of the trigger to setup
            config: Trigger configuration
            webhook_url: Webhook URL for webhook triggers
            
        Returns:
            Setup result with trigger ID and configuration
        """
        pass
    
    @abstractmethod
    async def remove_trigger(self, trigger_id: str) -> bool:
        """
        Remove a trigger
        
        Args:
            trigger_id: ID of the trigger to remove
            
        Returns:
            True if removal successful, False otherwise
        """
        pass
    
    async def validate_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate credentials against the auth config
        
        Args:
            credentials: Credentials to validate
            
        Returns:
            Validation result
        """
        if not self.auth_config:
            return {"valid": False, "error": "No auth configuration"}
        
        missing_fields = []
        for field in self.auth_config.required_fields:
            if field not in credentials:
                missing_fields.append(field)
        
        if missing_fields:
            return {
                "valid": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }
        
        return {"valid": True}
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to the external service
        
        Returns:
            Connection test result
        """
        try:
            if not self.is_authenticated:
                return {"connected": False, "error": "Not authenticated"}
            
            # Default implementation - subclasses should override
            return {"connected": True, "message": "Connection successful"}
        except Exception as e:
            logger.error(f"Connection test failed for {self.name}: {str(e)}")
            return {"connected": False, "error": str(e)}
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the complete schema for this connector
        
        Returns:
            Connector schema
        """
        return {
            "name": self.name,
            "version": self.version,
            "auth": self.auth_config.__dict__ if self.auth_config else None,
            "triggers": {
                name: {
                    "name": trigger.name,
                    "description": trigger.description,
                    "type": trigger.trigger_type.value,
                    "input_schema": trigger.input_schema,
                    "webhook_config": trigger.webhook_config,
                    "polling_config": trigger.polling_config
                }
                for name, trigger in self.triggers.items()
            },
            "actions": {
                name: {
                    "name": action.name,
                    "description": action.description,
                    "type": action.action_type.value,
                    "input_schema": action.input_schema,
                    "output_schema": action.output_schema,
                    "rate_limit": action.rate_limit
                }
                for name, action in self.actions.items()
            },
            "metadata": self.metadata
        }
    
    async def handle_webhook(self, trigger_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming webhook data
        
        Args:
            trigger_id: ID of the trigger
            data: Webhook data
            
        Returns:
            Processed webhook data
        """
        # Default implementation - subclasses should override
        return {"processed": True, "data": data}
    
    async def poll_trigger(self, trigger_id: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Poll for trigger events
        
        Args:
            trigger_id: ID of the trigger
            config: Polling configuration
            
        Returns:
            List of events
        """
        # Default implementation - subclasses should override
        return []
    
    def get_rate_limit_info(self, action_name: str = None) -> Dict[str, Any]:
        """
        Get rate limit information
        
        Args:
            action_name: Specific action name (optional)
            
        Returns:
            Rate limit information
        """
        if action_name and action_name in self.actions:
            return self.actions[action_name].rate_limit
        
        return {
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "requests_per_day": 10000
        }

class ConnectorRegistry:
    """Registry for managing connectors"""
    
    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {}
        self._connector_classes: Dict[str, type] = {}
    
    def register(self, connector_class: type):
        """Register a connector class"""
        # Create a temporary instance to get the name
        temp_instance = connector_class()
        self._connector_classes[temp_instance.name] = connector_class
        logger.info(f"Registered connector class: {temp_instance.name}")
    
    def create_instance(self, name: str, **kwargs) -> BaseConnector:
        """Create a new connector instance"""
        if name not in self._connector_classes:
            raise ValueError(f"Connector {name} not registered")
        
        connector_class = self._connector_classes[name]
        instance = connector_class(**kwargs)
        self._connectors[f"{name}_{id(instance)}"] = instance
        return instance
    
    def get_instance(self, instance_id: str) -> Optional[BaseConnector]:
        """Get a connector instance by ID"""
        return self._connectors.get(instance_id)
    
    def list_connectors(self) -> List[str]:
        """List all registered connector names"""
        return list(self._connector_classes.keys())
    
    def get_connector_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get the schema for a connector type"""
        if name not in self._connector_classes:
            return None
        
        temp_instance = self._connector_classes[name]()
        return temp_instance.get_schema()

# Global connector registry
connector_registry = ConnectorRegistry()
