"""
Weather connector for real-time weather data
"""

import os
import requests
from datetime import datetime
from typing import Any, Dict
import logging
from agent_system.agent import RealTimeConnection

logger = logging.getLogger(__name__)

class WeatherConnection(RealTimeConnection):
    """Weather connection for real-time weather data"""
    def __init__(self, config=None):
        super().__init__("weather", "Weather")
        self.config = config or {}
        self.api_key = None  # Will be set when configuring
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
        # Only try to get API key from environment if no config provided
        if not self.config:
            self.api_key = os.getenv('WEATHER_API_KEY')
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """Configure the connection with API key"""
        try:
            self.config.update(config)
            self.api_key = self.config.get('api_key') or self.api_key
            logger.info("Weather connection configured")
            return True
        except Exception as e:
            logger.error(f"Failed to configure Weather connection: {e}")
            return False
        
    def connect(self) -> bool:
        try:
            # Validate API key at connection time
            if not self.api_key:
                logger.error("Weather API key not configured. Please configure the connection first.")
                return False
                
            # Test connection with a simple API call
            response = requests.get(
                f"{self.base_url}/weather",
                params={
                    'q': 'London',
                    'appid': self.api_key
                }
            )
            
            if response.status_code == 200:
                self.is_connected = True
                logger.info("Connected to Weather API")
                return True
            else:
                logger.error(f"Weather API connection failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Weather connection error: {e}")
            return False
            
    def disconnect(self):
        self.is_connected = False
        logger.info("Weather disconnected")
        
    def send_data(self, data: Any) -> bool:
        # Weather API is read-only, so send_data is not applicable
        logger.info("Weather API is read-only")
        return False
        
    def receive_data(self) -> Any:
        # Mock receiving weather data
        return {
            "type": "weather_update",
            "location": "New York",
            "temperature": 72,
            "humidity": 65,
            "description": "Partly cloudy",
            "timestamp": datetime.now().isoformat()
        }
        
    def get_weather(self, location: str) -> Dict[str, Any]:
        """Get current weather for a location"""
        if not self.is_connected:
            return {"success": False, "error": "Not connected to weather API"}
            
        try:
            response = requests.get(
                f"{self.base_url}/weather",
                params={
                    'q': location,
                    'appid': self.api_key,
                    'units': 'metric'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "location": data['name'],
                    "temperature": data['main']['temp'],
                    "humidity": data['main']['humidity'],
                    "description": data['weather'][0]['description'],
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Failed to get weather data: {e}")
            return {"success": False, "error": str(e)}
