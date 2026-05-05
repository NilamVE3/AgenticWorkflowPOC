"""
Weather tools for weather data operations
"""

import os
import requests
from datetime import datetime
from typing import Dict, Any
import logging
from agent_system.agent import AgentTool

logger = logging.getLogger(__name__)

class WeatherTool(AgentTool):
    """Weather API integration for weather data operations"""
    def __init__(self):
        super().__init__(
            name="weather",
            description="Weather API integration for getting current weather, forecasts, and weather alerts",
            parameters={
                "operation": {"type": "string", "description": "Operation: current, forecast, alerts"},
                "location": {"type": "string", "description": "City name or coordinates (lat,lon)"},
                "units": {"type": "string", "description": "Units: metric, imperial, kelvin (default: metric)"},
                "days": {"type": "integer", "description": "Number of days for forecast (1-5)"}
            }
        )
        self.is_realtime = True
        self.api_key = os.getenv('WEATHER_API_KEY')
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
    def execute(self, **kwargs) -> Dict[str, Any]:
        operation = kwargs.get('operation', 'current')
        location = kwargs.get('location')
        
        if not self.api_key:
            return {"success": False, "error": "Weather API key not configured"}
            
        if not location:
            return {"success": False, "error": "Location is required"}
        
        try:
            if operation == 'current':
                return self._get_current_weather(kwargs)
            elif operation == 'forecast':
                return self._get_forecast(kwargs)
            elif operation == 'alerts':
                return self._get_weather_alerts(kwargs)
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_current_weather(self, kwargs: Dict) -> Dict[str, Any]:
        """Get current weather for a location"""
        location = kwargs.get('location')
        units = kwargs.get('units', 'metric')
        
        params = {
            'q': location,
            'appid': self.api_key,
            'units': units
        }
        
        response = requests.get(f"{self.base_url}/weather", params=params)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "location": data['name'],
                "country": data['sys']['country'],
                "temperature": data['main']['temp'],
                "feels_like": data['main']['feels_like'],
                "humidity": data['main']['humidity'],
                "pressure": data['main']['pressure'],
                "description": data['weather'][0]['description'],
                "wind_speed": data.get('wind', {}).get('speed', 0),
                "wind_direction": data.get('wind', {}).get('deg', 0),
                "visibility": data.get('visibility', 0),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {"success": False, "error": response.text}
    
    def _get_forecast(self, kwargs: Dict) -> Dict[str, Any]:
        """Get weather forecast for a location"""
        location = kwargs.get('location')
        units = kwargs.get('units', 'metric')
        days = min(kwargs.get('days', 3), 5)  # Limit to 5 days max
        
        params = {
            'q': location,
            'appid': self.api_key,
            'units': units,
            'cnt': days * 8  # 8 forecasts per day (3-hour intervals)
        }
        
        response = requests.get(f"{self.base_url}/forecast", params=params)
        
        if response.status_code == 200:
            data = response.json()
            forecasts = []
            
            for item in data['list']:
                forecasts.append({
                    'datetime': item['dt_txt'],
                    'temperature': item['main']['temp'],
                    'feels_like': item['main']['feels_like'],
                    'humidity': item['main']['humidity'],
                    'description': item['weather'][0]['description'],
                    'wind_speed': item.get('wind', {}).get('speed', 0),
                    'precipitation': item.get('rain', {}).get('3h', 0)
                })
            
            return {
                "success": True,
                "location": data['city']['name'],
                "country": data['city']['country'],
                "forecasts": forecasts,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {"success": False, "error": response.text}
    
    def _get_weather_alerts(self, kwargs: Dict) -> Dict[str, Any]:
        """Get weather alerts for a location"""
        location = kwargs.get('location')
        
        # OpenWeatherMap requires coordinates for alerts
        # First get coordinates from location name
        geo_params = {
            'q': location,
            'limit': 1,
            'appid': self.api_key
        }
        
        geo_response = requests.get("http://api.openweathermap.org/geo/1.0/direct", params=geo_params)
        
        if geo_response.status_code != 200:
            return {"success": False, "error": "Could not find location coordinates"}
        
        geo_data = geo_response.json()
        if not geo_data:
            return {"success": False, "error": "Location not found"}
        
        lat = geo_data[0]['lat']
        lon = geo_data[0]['lat']
        
        # Get alerts using One Call API
        alert_params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'exclude': 'minutely,hourly,daily'
        }
        
        response = requests.get(f"{self.base_url}/onecall", params=alert_params)
        
        if response.status_code == 200:
            data = response.json()
            alerts = data.get('alerts', [])
            
            return {
                "success": True,
                "location": location,
                "alerts": [{
                    'event': alert.get('event', ''),
                    'start': alert.get('start', ''),
                    'end': alert.get('end', ''),
                    'description': alert.get('description', ''),
                    'severity': alert.get('severity', '')
                } for alert in alerts],
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {"success": False, "error": response.text}
