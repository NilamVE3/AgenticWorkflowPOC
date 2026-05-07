"""
API Server - Start only the backend API
"""

import os
import asyncio
import logging
from api.routes.main_api import app
from main import initialize_platform

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        # Initialize platform components
        logger.info("Initializing Integration Platform...")
        asyncio.run(initialize_platform())
        
        # Print startup information
        logger.info("=" * 50)
        logger.info("Integration Platform API is ready!")
        logger.info("=" * 50)
        logger.info("API Documentation: http://localhost:8000/docs")
        logger.info("Health Check: http://localhost:8000/health")
        logger.info("System Info: http://localhost:8000/api/system/info")
        logger.info("=" * 50)
        
        # Start API server
        import uvicorn
        uvicorn.run(
            app,
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            log_level="info"
        )
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")

if __name__ == "__main__":
    main()
