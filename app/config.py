from pydantic_settings import BaseSettings
import os 
class Settings(BaseSettings):
    # Replace with your actual PostgreSQL credentials
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    class Config:
        env_file = ".env"

settings = Settings()
