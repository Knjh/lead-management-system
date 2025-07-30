# config/settings.py
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field # Import Field for excluding from validation
import pytz

class Settings(BaseSettings):
    # Firebase
    firebase_service_account_path: str = "service.json"
    firebase_project_id: str
    firebase_query_limit: int = 50
    
    # Retell API
    retell_api_key: str
    retell_base_url: str = "https://api.retellai.com"
    retell_webhook_secret: Optional[str] = None
    retell_agent_id: str
    retell_phone_number: str

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    webhook_base_url: str  # Your public URL for webhooks
    
    # Calling configuration
    max_concurrent_calls: int = 15
    max_retries: int = 3
    cron_interval_minutes: int = 10
    calling_start_hour: int = 9  # 10 AM
    calling_end_hour: int = 17    # 11 PM (originally 5 PM, changed to 11 PM based on common calling hours)
    calling_end_minute: int = 30  # 5:30 PM (now 11:30 PM)
    
    app_timezone: str = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
    
    # FIX: Use Field(None, exclude=True) to tell Pydantic to ignore this field during initial validation
    app_timezone_obj: Optional[pytz.timezone] = Field(None, exclude=True)

    class Config:
        env_file = ".env"

# Create an instance of Settings
settings = Settings()

# Post-initialization to set the timezone object
try:
    settings.app_timezone_obj = pytz.timezone(settings.app_timezone)
except pytz.UnknownTimeZoneError:
    print(f"Warning: Unknown timezone '{settings.app_timezone}'. Falling back to UTC.")
    settings.app_timezone_obj = pytz.utc