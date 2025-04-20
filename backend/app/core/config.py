from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv
from pydantic import ConfigDict

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # API Keys
    HEVY_API_KEY: str
    OPENAI_API_KEY: str

    # Database - REMOVED
    # DATABASE_URL: str = "sqlite:///./workout_optimizer.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Application Settings
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "your_secret_key_here"

    # Frontend Settings
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"

    model_config = ConfigDict(env_file=".env", case_sensitive=True, extra="allow")

@lru_cache()
def get_settings() -> Settings:
    return Settings() 