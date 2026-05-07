"""
UI Server - Simple web server for the Integration Platform UI
"""

import os
import asyncio
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

# Create FastAPI app for UI
ui_app = FastAPI(title="Integration Platform UI")

# Get the directory where this script is located
current_dir = Path(__file__).parent

# Mount static files
ui_app.mount("/static", StaticFiles(directory=current_dir / "static"), name="static")

@ui_app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the main UI page"""
    index_path = current_dir / "index.html"
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@ui_app.get("/health")
async def ui_health():
    """UI health check"""
    return {"status": "healthy", "service": "ui"}

def run_ui_server(host="0.0.0.0", port=3000):
    """Run the UI server"""
    print(f"🌐 Starting UI Server on http://{host}:{port}")
    print("📱 Integration Platform UI is ready!")
    print("🎯 Navigate to: http://localhost:3000")
    print("🔗 API Backend: http://localhost:8000")
    
    uvicorn.run(
        ui_app,
        host=host,
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    run_ui_server()
