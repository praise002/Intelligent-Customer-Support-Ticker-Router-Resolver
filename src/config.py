from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"
    # redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


Config = Settings()
