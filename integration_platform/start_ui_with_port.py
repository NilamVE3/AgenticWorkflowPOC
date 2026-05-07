
# UI Server with correct API port
import os
import uvicorn
from ui.server import run_ui_server

if __name__ == "__main__":
    print("Starting UI Server...")
    print("API Backend: http://localhost:8000")
    print("Web Interface: http://localhost:3000")
    run_ui_server(host="0.0.0.0", port=3000)
