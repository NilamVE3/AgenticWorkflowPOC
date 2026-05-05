"""
Slack tools for messaging and workspace operations
"""

import os
import requests
from typing import Dict, Any
import logging
from agent_system.agent import AgentTool

logger = logging.getLogger(__name__)

class SlackTool(AgentTool):
    """Slack API integration for messaging and workspace operations"""
    def __init__(self):
        super().__init__(
            name="slack",
            description="Slack API integration for sending messages, managing channels, and workspace operations",
            parameters={
                "operation": {"type": "string", "description": "Operation: send_message, list_channels, get_users, post_file"},
                "channel": {"type": "string", "description": "Channel name or ID"},
                "message": {"type": "string", "description": "Message to send"},
                "file_path": {"type": "string", "description": "File path to upload (for post_file)"},
                "user_id": {"type": "string", "description": "User ID for user operations"}
            }
        )
        self.is_realtime = True
        self.bot_token = os.getenv('SLACK_BOT_TOKEN')
        self.user_token = os.getenv('SLACK_USER_TOKEN')
        
    def _get_headers(self, use_user_token: bool = False) -> Dict[str, str]:
        """Get authenticated headers for Slack API"""
        token = self.user_token if use_user_token else self.bot_token
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        operation = kwargs.get('operation')
        
        if not self.bot_token:
            return {"success": False, "error": "Slack bot token not configured"}
        
        try:
            if operation == 'send_message':
                return self._send_message(kwargs)
            elif operation == 'list_channels':
                return self._list_channels()
            elif operation == 'get_users':
                return self._get_users()
            elif operation == 'post_file':
                return self._post_file(kwargs)
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _send_message(self, kwargs: Dict) -> Dict[str, Any]:
        """Send message to Slack channel"""
        channel = kwargs.get('channel')
        message = kwargs.get('message')
        
        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers=self._get_headers(),
            json={
                'channel': channel,
                'text': message
            }
        )
        
        data = response.json()
        return {
            "success": data.get('ok', False),
            "message": "Message sent successfully" if data.get('ok') else data.get('error'),
            "ts": data.get('ts'),
            "channel": data.get('channel')
        }
    
    def _list_channels(self) -> Dict[str, Any]:
        """List Slack channels"""
        response = requests.get(
            'https://slack.com/api/conversations.list',
            headers=self._get_headers(),
            params={'types': 'public_channel,private_channel'}
        )
        
        data = response.json()
        if data.get('ok'):
            channels = [{'id': ch['id'], 'name': ch['name'], 'type': ch.get('is_private', False)} 
                       for ch in data.get('channels', [])]
            return {"success": True, "channels": channels}
        else:
            return {"success": False, "error": data.get('error')}
    
    def _get_users(self) -> Dict[str, Any]:
        """Get Slack users list"""
        response = requests.get(
            'https://slack.com/api/users.list',
            headers=self._get_headers()
        )
        
        data = response.json()
        if data.get('ok'):
            users = [{'id': u['id'], 'name': u['name'], 'real_name': u.get('real_name', '')} 
                    for u in data.get('members', []) if not u.get('deleted')]
            return {"success": True, "users": users}
        else:
            return {"success": False, "error": data.get('error')}
    
    def _post_file(self, kwargs: Dict) -> Dict[str, Any]:
        """Upload file to Slack"""
        channel = kwargs.get('channel')
        file_path = kwargs.get('file_path')
        
        if not os.path.exists(file_path):
            return {"success": False, "error": "File not found"}
        
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'channels': channel,
                'initial_comment': f'Uploading file: {os.path.basename(file_path)}'
            }
            
            response = requests.post(
                'https://slack.com/api/files.upload',
                headers={'Authorization': f'Bearer {self.bot_token}'},
                files=files,
                data=data
            )
        
        result = response.json()
        return {
            "success": result.get('ok', False),
            "message": "File uploaded successfully" if result.get('ok') else result.get('error'),
            "file_id": result.get('file', {}).get('id')
        }
