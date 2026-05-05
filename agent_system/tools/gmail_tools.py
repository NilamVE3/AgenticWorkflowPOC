"""
Gmail tools for email operations
"""

import os
import base64
import requests
from typing import Dict, Any
import logging
from agent_system.agent import AgentTool

logger = logging.getLogger(__name__)

class GmailTool(AgentTool):
    """Gmail API integration for email operations"""
    def __init__(self):
        super().__init__(
            name="gmail",
            description="Gmail API integration for sending, reading, and managing emails",
            parameters={
                "operation": {"type": "string", "description": "Operation: send, read, search, delete"},
                "to": {"type": "string", "description": "Recipient email (for send)"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body"},
                "query": {"type": "string", "description": "Search query (for search)"},
                "message_id": {"type": "string", "description": "Message ID (for read/delete)"}
            }
        )
        self.is_realtime = True
        self.access_token = os.getenv('GMAIL_ACCESS_TOKEN')
        self.refresh_token = os.getenv('GMAIL_REFRESH_TOKEN')
        self.client_id = os.getenv('GMAIL_CLIENT_ID')
        self.client_secret = os.getenv('GMAIL_CLIENT_SECRET')
        
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
        
    def execute(self, **kwargs) -> Dict[str, Any]:
        operation = kwargs.get('operation')
        
        if not self.access_token and not self._refresh_access_token():
            return {"success": False, "error": "No valid Gmail access token"}
        
        headers = self._get_headers()
        
        try:
            if operation == 'send':
                return self._send_email(headers, kwargs)
            elif operation == 'read':
                return self._read_email(headers, kwargs)
            elif operation == 'search':
                return self._search_emails(headers, kwargs)
            elif operation == 'delete':
                return self._delete_email(headers, kwargs)
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _send_email(self, headers: Dict, kwargs: Dict) -> Dict[str, Any]:
        """Send email via Gmail API"""
        to = kwargs.get('to')
        subject = kwargs.get('subject')
        body = kwargs.get('body', '')
        
        message = {
            'raw': base64.urlsafe_b64encode(
                f"From: me\r\nTo: {to}\r\nSubject: {subject}\r\n\r\n{body}".encode()
            ).decode()
        }
        
        response = requests.post(
            'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
            headers=headers,
            json=message
        )
        
        if response.status_code == 200:
            return {
                "success": True,
                "message_id": response.json()['id'],
                "message": "Email sent successfully"
            }
        else:
            return {"success": False, "error": response.text}
    
    def _read_email(self, headers: Dict, kwargs: Dict) -> Dict[str, Any]:
        """Read email by ID"""
        message_id = kwargs.get('message_id')
        
        response = requests.get(
            f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            message = response.json()
            return {
                "success": True,
                "message": self._parse_message(message)
            }
        else:
            return {"success": False, "error": response.text}
    
    def _search_emails(self, headers: Dict, kwargs: Dict) -> Dict[str, Any]:
        """Search emails"""
        query = kwargs.get('query', '')
        
        response = requests.get(
            f'https://gmail.googleapis.com/gmail/v1/users/me/messages',
            headers=headers,
            params={'q': query}
        )
        
        if response.status_code == 200:
            messages = response.json().get('messages', [])
            return {
                "success": True,
                "messages": messages[:10],  # Limit to 10 results
                "total": len(messages)
            }
        else:
            return {"success": False, "error": response.text}
    
    def _delete_email(self, headers: Dict, kwargs: Dict) -> Dict[str, Any]:
        """Delete email by ID"""
        message_id = kwargs.get('message_id')
        
        response = requests.delete(
            f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}',
            headers=headers
        )
        
        if response.status_code == 204:
            return {"success": True, "message": "Email deleted successfully"}
        else:
            return {"success": False, "error": response.text}
    
    def _parse_message(self, message: Dict) -> Dict[str, Any]:
        """Parse Gmail message format"""
        headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}
        return {
            'id': message['id'],
            'subject': headers.get('Subject', ''),
            'from': headers.get('From', ''),
            'date': headers.get('Date', ''),
            'snippet': message.get('snippet', '')
        }
