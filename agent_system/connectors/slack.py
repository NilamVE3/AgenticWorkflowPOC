"""
Slack connector for real-time Slack API integration
"""

import os
import requests
from typing import Any, Dict
import logging
from agent_system.agent import RealTimeConnection

logger = logging.getLogger(__name__)

class SlackConnection(RealTimeConnection):
    """Slack connection for real-time messaging and events"""
    def __init__(self, config=None):
        super().__init__("slack", "Slack")
        self.config = config or {}
        self.bot_token = None  # Will be set when configuring
        self.user_token = None  # Will be set when configuring
        self.socket_mode_token = None  # Will be set when configuring
        self.app_token = None  # Will be set when configuring
        
        # Only try to get tokens from environment if no config provided
        if not self.config:
            self.bot_token = os.getenv('SLACK_BOT_TOKEN')
            self.user_token = os.getenv('SLACK_USER_TOKEN')
            self.socket_mode_token = os.getenv('SLACK_SOCKET_MODE_TOKEN')
            self.app_token = os.getenv('SLACK_APP_TOKEN')
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """Configure the connection with API keys"""
        try:
            self.config.update(config)
            self.bot_token = self.config.get('bot_token') or self.bot_token
            self.user_token = self.config.get('user_token') or self.user_token
            self.socket_mode_token = self.config.get('socket_mode_token') or self.socket_mode_token
            self.app_token = self.config.get('app_token') or self.app_token
            logger.info("Slack connection configured")
            return True
        except Exception as e:
            logger.error(f"Failed to configure Slack connection: {e}")
            return False
        
    def _get_headers(self, use_user_token: bool = False) -> Dict[str, str]:
        """Get authenticated headers for Slack API"""
        token = self.user_token if use_user_token else self.bot_token
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def connect(self) -> bool:
        try:
            # Validate API key at connection time
            if not self.bot_token:
                logger.error("Slack bot token not configured. Please configure the connection first.")
                return False
                
            # Test connection by getting auth info
            response = requests.get(
                'https://slack.com/api/auth.test',
                headers=self._get_headers()
            )
            
            if response.json().get('ok'):
                self.is_connected = True
                logger.info("Connected to Slack API")
                return True
            else:
                logger.error(f"Slack auth failed: {response.json().get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Slack connection failed: {e}")
            return False
            
    def disconnect(self):
        self.is_connected = False
        logger.info("Slack disconnected")
        
    def send_data(self, data: Any) -> bool:
        if not self.is_connected:
            return False
            
        try:
            # Send message to Slack
            if isinstance(data, dict) and 'channel' in data and 'message' in data:
                response = requests.post(
                    'https://slack.com/api/chat.postMessage',
                    headers=self._get_headers(),
                    json={
                        'channel': data['channel'],
                        'text': data['message']
                    }
                )
                return response.json().get('ok', False)
            return False
        except Exception as e:
            logger.error(f"Failed to send Slack data: {e}")
            return False
        
    def receive_data(self) -> Any:
        # Mock receiving Slack events
        return {
            "type": "message",
            "channel": "general",
            "user": "user123",
            "text": "Hello from Slack",
            "timestamp": "1234567890.123456"
        }
