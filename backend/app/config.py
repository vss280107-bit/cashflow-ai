from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./cashflow.db"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 60 * 24
    field_encryption_key: str = ""
    cors_origins: str = "http://localhost:5173"


settings = Settings()
