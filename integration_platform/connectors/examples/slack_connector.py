"""
Slack Connector - Example connector implementation
"""

from typing import Dict, Any, List, Optional
import asyncio
import logging
from connectors.sdk.base_connector import (
    BaseConnector, AuthenticationConfig, AuthenticationType,
    TriggerDefinition, ActionDefinition, TriggerType, ActionType
)

logger = logging.getLogger(__name__)

class SlackConnector(BaseConnector):
    """Slack connector for messaging and channel management"""
    
    def __init__(self):
        super().__init__("slack", "1.0.0")
        
        # Set authentication configuration
        self.auth_config = AuthenticationConfig(
            auth_type=AuthenticationType.BEARER_TOKEN,
            required_fields=["bot_token"],
            optional_fields=["user_token", "app_token"],
            token_refresh_config={"enabled": False}
        )
        
        # Define actions
        self.actions = {
            "send_message": ActionDefinition(
                name="send_message",
                description="Send a message to a Slack channel",
                action_type=ActionType.CREATE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Channel ID or name"},
                        "message": {"type": "string", "description": "Message to send"},
                        "thread_ts": {"type": "string", "description": "Thread timestamp for replies"}
                    },
                    "required": ["channel", "message"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "ok": {"type": "boolean"},
                        "ts": {"type": "string"},
                        "message": {"type": "object"}
                    }
                }
            ),
            "create_channel": ActionDefinition(
                name="create_channel",
                description="Create a new Slack channel",
                action_type=ActionType.CREATE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Channel name"},
                        "is_private": {"type": "boolean", "description": "Make channel private"},
                        "description": {"type": "string", "description": "Channel description"}
                    },
                    "required": ["name"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "ok": {"type": "boolean"},
                        "channel": {"type": "object"}
                    }
                }
            ),
            "list_channels": ActionDefinition(
                name="list_channels",
                description="List all channels",
                action_type=ActionType.READ,
                input_schema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Maximum number of channels to return"},
                        "exclude_archived": {"type": "boolean", "description": "Exclude archived channels"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "ok": {"type": "boolean"},
                        "channels": {"type": "array"}
                    }
                }
            ),
            "upload_file": ActionDefinition(
                name="upload_file",
                description="Upload a file to a channel",
                action_type=ActionType.CREATE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Channel ID"},
                        "file_path": {"type": "string", "description": "Path to file"},
                        "title": {"type": "string", "description": "File title"},
                        "initial_comment": {"type": "string", "description": "Initial comment"}
                    },
                    "required": ["channel", "file_path"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "ok": {"type": "boolean"},
                        "file": {"type": "object"}
                    }
                }
            ),
            "get_user_info": ActionDefinition(
                name="get_user_info",
                description="Get information about a user",
                action_type=ActionType.READ,
                input_schema={
                    "type": "object",
                    "properties": {
                        "user": {"type": "string", "description": "User ID"}
                    },
                    "required": ["user"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "ok": {"type": "boolean"},
                        "user": {"type": "object"}
                    }
                }
            )
        }
        
        # Define triggers
        self.triggers = {
            "new_message": TriggerDefinition(
                name="new_message",
                description="Trigger on new messages in channel",
                trigger_type=TriggerType.WEBHOOK,
                input_schema={
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Channel to monitor"},
                        "webhook_url": {"type": "string", "description": "Webhook URL"}
                    },
                    "required": ["channel", "webhook_url"]
                },
                webhook_config={
                    "events": ["message"],
                    "filters": ["subtype: null"]  # Only actual messages, not subtypes
                }
            ),
            "channel_created": TriggerDefinition(
                name="channel_created",
                description="Trigger when a new channel is created",
                trigger_type=TriggerType.WEBHOOK,
                input_schema={
                    "type": "object",
                    "properties": {
                        "webhook_url": {"type": "string", "description": "Webhook URL"}
                    },
                    "required": ["webhook_url"]
                },
                webhook_config={
                    "events": ["channel_created"]
                }
            )
        }
    
    def get_auth_config(self) -> AuthenticationConfig:
        return self.auth_config
    
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate with Slack"""
        self.credentials = credentials
        bot_token = credentials.get("bot_token")
        
        if not bot_token:
            return False
        
        try:
            # Test authentication by calling auth.test
            result = await self._make_slack_request("auth.test", {})
            self.is_authenticated = result.get("ok", False)
            return self.is_authenticated
        except Exception as e:
            logger.error(f"Slack authentication failed: {str(e)}")
            return False
    
    async def refresh_token(self) -> bool:
        """Slack tokens don't expire, so no refresh needed"""
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
        """Execute a Slack action"""
        if not self.is_authenticated:
            return {"success": False, "error": "Not authenticated"}
        
        try:
            if action_name == "send_message":
                return await self._send_message(input_data)
            elif action_name == "create_channel":
                return await self._create_channel(input_data)
            elif action_name == "list_channels":
                return await self._list_channels(input_data)
            elif action_name == "upload_file":
                return await self._upload_file(input_data)
            elif action_name == "get_user_info":
                return await self._get_user_info(input_data)
            else:
                return {"success": False, "error": f"Unknown action: {action_name}"}
        
        except Exception as e:
            logger.error(f"Slack action {action_name} failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def setup_trigger(
        self,
        trigger_name: str,
        config: Dict[str, Any],
        webhook_url: str = None
    ) -> Dict[str, Any]:
        """Setup a Slack trigger"""
        if not self.is_authenticated:
            return {"success": False, "error": "Not authenticated"}
        
        try:
            if trigger_name == "new_message":
                return await self._setup_message_trigger(config, webhook_url)
            elif trigger_name == "channel_created":
                return await self._setup_channel_trigger(config, webhook_url)
            else:
                return {"success": False, "error": f"Unknown trigger: {trigger_name}"}
        
        except Exception as e:
            logger.error(f"Slack trigger {trigger_name} setup failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def remove_trigger(self, trigger_id: str) -> bool:
        """Remove a Slack trigger"""
        try:
            # Unsubscribe from events
            await self._make_slack_request("apps.event.subscriptions.delete", {
                "trigger_id": trigger_id
            })
            return True
        except Exception as e:
            logger.error(f"Failed to remove Slack trigger: {str(e)}")
            return False
    
    async def _send_message(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to a channel"""
        params = {
            "channel": input_data["channel"],
            "text": input_data["message"]
        }
        
        if "thread_ts" in input_data:
            params["thread_ts"] = input_data["thread_ts"]
        
        result = await self._make_slack_request("chat.postMessage", params)
        
        if result.get("ok"):
            return {
                "success": True,
                "data": {
                    "message_ts": result.get("ts"),
                    "channel": result.get("channel")
                }
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error")
            }
    
    async def _create_channel(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new channel"""
        params = {
            "name": input_data["name"]
        }
        
        if input_data.get("is_private"):
            params["is_private"] = True
        
        if "description" in input_data:
            params["purpose"] = input_data["description"]
        
        result = await self._make_slack_request("conversations.create", params)
        
        if result.get("ok"):
            return {
                "success": True,
                "data": {
                    "channel_id": result["channel"]["id"],
                    "name": result["channel"]["name"]
                }
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error")
            }
    
    async def _list_channels(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """List channels"""
        params = {}
        
        if "limit" in input_data:
            params["limit"] = input_data["limit"]
        
        if "exclude_archived" in input_data:
            params["exclude_archived"] = input_data["exclude_archived"]
        
        result = await self._make_slack_request("conversations.list", params)
        
        if result.get("ok"):
            return {
                "success": True,
                "data": {
                    "channels": result.get("channels", []),
                    "total": len(result.get("channels", []))
                }
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error")
            }
    
    async def _upload_file(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Upload a file to a channel"""
        import aiohttp
        
        # Read file content
        try:
            with open(input_data["file_path"], "rb") as f:
                file_content = f.read()
        except Exception as e:
            return {"success": False, "error": f"Failed to read file: {str(e)}"}
        
        # Prepare multipart form data
        data = aiohttp.FormData()
        data.add_field("file", file_content, filename=input_data["file_path"])
        data.add_field("channels", input_data["channel"])
        
        if "title" in input_data:
            data.add_field("title", input_data["title"])
        
        if "initial_comment" in input_data:
            data.add_field("initial_comment", input_data["initial_comment"])
        
        # Make request
        headers = {"Authorization": f"Bearer {self.credentials['bot_token']}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://slack.com/api/files.upload",
                headers=headers,
                data=data
            ) as response:
                result = await response.json()
                
                if result.get("ok"):
                    return {
                        "success": True,
                        "data": {
                            "file_id": result["file"]["id"],
                            "name": result["file"]["name"],
                            "url": result["file"]["url_private"]
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("error", "Unknown error")
                    }
    
    async def _get_user_info(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get user information"""
        params = {"user": input_data["user"]}
        
        result = await self._make_slack_request("users.info", params)
        
        if result.get("ok"):
            return {
                "success": True,
                "data": result.get("user", {})
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error")
            }
    
    async def _setup_message_trigger(self, config: Dict[str, Any], webhook_url: str) -> Dict[str, Any]:
        """Setup message trigger"""
        # Subscribe to message events
        event_subscriptions = {
            "type": "event_subscriptions",
            "request_url": webhook_url,
            "event_types": ["message"],
            "filter": {
                "channel": config["channel"]
            }
        }
        
        result = await self._make_slack_request("apps.event.subscriptions.create", event_subscriptions)
        
        if result.get("ok"):
            return {
                "success": True,
                "trigger_id": result.get("trigger_id"),
                "message": "Message trigger setup successful"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error")
            }
    
    async def _setup_channel_trigger(self, config: Dict[str, Any], webhook_url: str) -> Dict[str, Any]:
        """Setup channel creation trigger"""
        event_subscriptions = {
            "type": "event_subscriptions",
            "request_url": webhook_url,
            "event_types": ["channel_created"]
        }
        
        result = await self._make_slack_request("apps.event.subscriptions.create", event_subscriptions)
        
        if result.get("ok"):
            return {
                "success": True,
                "trigger_id": result.get("trigger_id"),
                "message": "Channel trigger setup successful"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error")
            }
    
    async def _make_slack_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to Slack API"""
        import aiohttp
        
        url = f"https://slack.com/api/{method}"
        headers = {
            "Authorization": f"Bearer {self.credentials['bot_token']}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=params) as response:
                return await response.json()

# Register the connector
from connectors.sdk.base_connector import connector_registry
connector_registry.register(SlackConnector)
