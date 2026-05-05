"""
File operation tools for basic file system operations
"""

import os
from typing import Dict, Any
import logging
from agent_system.agent import AgentTool

logger = logging.getLogger(__name__)

class FileOperationTool(AgentTool):
    """Tool for file operations"""
    def __init__(self):
        super().__init__(
            name="file_operations",
            description="Perform file operations like read, write, delete",
            parameters={
                "action": {"type": "string", "description": "Action to perform (read/write/delete/list)"},
                "filename": {"type": "string", "description": "Target filename or directory path"},
                "content": {"type": "string", "description": "Content to write (for write action)"},
                "encoding": {"type": "string", "description": "File encoding (default: utf-8)"}
            }
        )
        
    def execute(self, **kwargs) -> Dict[str, Any]:
        action = kwargs.get('action')
        filename = kwargs.get('filename')
        encoding = kwargs.get('encoding', 'utf-8')
        
        try:
            if action == 'read':
                return self._read_file(filename, encoding)
            elif action == 'write':
                content = kwargs.get('content', '')
                return self._write_file(filename, content, encoding)
            elif action == 'delete':
                return self._delete_file(filename)
            elif action == 'list':
                return self._list_directory(filename)
            else:
                return {"success": False, "error": "Unknown action"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _read_file(self, filename: str, encoding: str) -> Dict[str, Any]:
        """Read file content"""
        try:
            with open(filename, 'r', encoding=encoding) as f:
                content = f.read()
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}
                
    def _write_file(self, filename: str, content: str, encoding: str) -> Dict[str, Any]:
        """Write content to file"""
        try:
            with open(filename, 'w', encoding=encoding) as f:
                f.write(content)
            return {"success": True, "message": f"Written to {filename}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
                
    def _delete_file(self, filename: str) -> Dict[str, Any]:
        """Delete file"""
        try:
            os.remove(filename)
            return {"success": True, "message": f"Deleted {filename}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _list_directory(self, path: str) -> Dict[str, Any]:
        """List directory contents"""
        try:
            items = []
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path)
                    items.append({"name": item, "type": "file", "size": size})
                else:
                    items.append({"name": item, "type": "directory", "size": 0})
            
            return {"success": True, "items": items}
        except Exception as e:
            return {"success": False, "error": str(e)}
