from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/sociallistener"

    # Bluesky
    bluesky_handle: str = ""
    bluesky_app_password: str = ""
    bluesky_poll_interval: int = 120  # seconds

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
