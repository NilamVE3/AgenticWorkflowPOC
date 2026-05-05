"""
Gmail connector for real-time email integration
"""

import os
import requests
from datetime import datetime
from typing import Any, Dict
import logging
from agent_system.agent import RealTimeConnection

logger = logging.getLogger(__name__)

class GmailConnection(RealTimeConnection):
    """Gmail connection for real-time email monitoring"""
    def __init__(self, config=None):
        super().__init__("gmail", "Gmail")
        self.config = config or {}
        self.access_token = None  # Will be set when configuring
        self.refresh_token = None  # Will be set when configuring
        self.client_id = None  # Will be set when configuring
        self.client_secret = None  # Will be set when configuring
        
        # Only try to get tokens from environment if no config provided
        if not self.config:
            self.access_token = os.getenv('GMAIL_ACCESS_TOKEN')
            self.refresh_token = os.getenv('GMAIL_REFRESH_TOKEN')
            self.client_id = os.getenv('GMAIL_CLIENT_ID')
            self.client_secret = os.getenv('GMAIL_CLIENT_SECRET')
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """Configure the connection with API keys"""
        try:
            self.config.update(config)
            self.access_token = self.config.get('access_token') or self.access_token
            self.refresh_token = self.config.get('refresh_token') or self.refresh_token
            self.client_id = self.config.get('client_id') or self.client_id
            self.client_secret = self.config.get('client_secret') or self.client_secret
            logger.info("Gmail connection configured")
            return True
        except Exception as e:
            logger.error(f"Failed to configure Gmail connection: {e}")
            return False
        
    def _get_headers(self) -> Dict[str, str]:
        """Get authenticated headers for Gmail API"""
        if self.access_token:
            return {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
        return {}
    
    def _refresh_access_token(self) -> bool:
        """Refresh Gmail access token"""
        if not self.refresh_token:
            return False
            
        try:
            response = requests.post('https://oauth2.googleapis.com/token', data={
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret
            })
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                return True
        except Exception as e:
            logger.error(f"Gmail token refresh failed: {e}")
        return False
        
    def connect(self) -> bool:
        try:
            # Validate API credentials at connection time
            if not self.access_token and not self._refresh_access_token():
                logger.error("No valid Gmail access token. Please configure the connection first.")
                return False
                
            # Test connection by getting user profile
            response = requests.get(
                'https://gmail.googleapis.com/gmail/v1/users/me/profile',
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                self.is_connected = True
                logger.info("Connected to Gmail API")
                return True
            else:
                logger.error(f"Gmail connection failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Gmail connection error: {e}")
            return False
            
    def disconnect(self):
        self.is_connected = False
        logger.info("Gmail disconnected")
        
    def send_data(self, data: Any) -> bool:
        if not self.is_connected:
            return False
            
        try:
            # Send email via Gmail
            if isinstance(data, dict) and 'to' in data and 'subject' in data:
                import base64
                
                message = {
                    'raw': base64.urlsafe_b64encode(
                        f"From: me\r\nTo: {data['to']}\r\nSubject: {data['subject']}\r\n\r\n{data.get('body', '')}".encode()
                    ).decode()
                }
                
                response = requests.post(
                    'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
                    headers=self._get_headers(),
                    json=message
                )
                
                return response.status_code == 200
            return False
        except Exception as e:
            logger.error(f"Failed to send Gmail data: {e}")
            return False
        
    def receive_data(self) -> Any:
        # Mock receiving new email notification
        return {
            "type": "new_email",
            "message_id": "12345",
            "subject": "New Email Received",
            "from": "sender@example.com",
            "timestamp": datetime.now().isoformat()
        }
