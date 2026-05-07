"""
Simple API Server - Direct uvicorn startup with platform initialization
"""

import os
import asyncio
import uvicorn
from api.routes.main_api import app
from main import initialize_platform

async def initialize_and_start():
    """Initialize platform components and start server"""
    try:
        # Initialize platform components
        print("Initializing Integration Platform components...")
        await initialize_platform()
        print("Platform components initialized successfully!")
        
        # Print startup information
        print("=" * 50)
        print("Integration Platform API is ready!")
        print("=" * 50)
        print("API Documentation: http://localhost:8000/docs")
        print("Health Check: http://localhost:8000/health")
        print("System Info: http://localhost:8000/api/system/info")
        print("=" * 50)
        
        # Start API server
        uvicorn.run(
            app,
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            log_level="info"
        )
        
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"Startup failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(initialize_and_start())
