"""
API tools for making HTTP requests
"""

import requests
from typing import Dict, Any
import logging
from agent_system.agent import AgentTool

logger = logging.getLogger(__name__)

class APICallTool(AgentTool):
    """Tool for making API calls"""
    def __init__(self):
        super().__init__(
            name="api_call",
            description="Make HTTP API calls",
            parameters={
                "url": {"type": "string", "description": "API endpoint URL"},
                "method": {"type": "string", "description": "HTTP method (GET/POST/PUT/DELETE)"},
                "headers": {"type": "object", "description": "Request headers"},
                "data": {"type": "object", "description": "Request data"},
                "params": {"type": "object", "description": "URL parameters"},
                "timeout": {"type": "integer", "description": "Request timeout in seconds"}
            }
        )
        self.is_realtime = True
        
    def execute(self, **kwargs) -> Dict[str, Any]:
        url = kwargs.get('url')
        method = kwargs.get('method', 'GET').upper()
        headers = kwargs.get('headers', {})
        data = kwargs.get('data', {})
        params = kwargs.get('params', {})
        timeout = kwargs.get('timeout', 30)
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, params=params, timeout=timeout)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data, params=params, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, params=params, timeout=timeout)
            elif method == 'PATCH':
                response = requests.patch(url, headers=headers, json=data, params=params, timeout=timeout)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}
                
            # Try to parse JSON response
            try:
                response_data = response.json()
            except:
                response_data = response.text
                
            return {
                "success": True,
                "status_code": response.status_code,
                "response": response_data,
                "headers": dict(response.headers),
                "url": response.url
            }
            
        except requests.exceptions.Timeout:
            return {"success": False, "error": f"Request timeout after {timeout} seconds"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Connection error"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}
