from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEVELOPMENT_SECRET = "development-only-change-this-secret-before-deployment"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SMARTCAMPUS_",
        env_file=".env",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str = "sqlite:///./smartcampus.db"
    jwt_secret_key: str = _DEVELOPMENT_SECRET
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    cookie_secure: bool = False
    auto_create_tables: bool = True

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env.lower() == "production":
            if self.jwt_secret_key == _DEVELOPMENT_SECRET or len(self.jwt_secret_key) < 32:
                raise ValueError("Set a unique JWT secret of at least 32 characters in production.")
            if not self.cookie_secure:
                raise ValueError("Secure cookies must be enabled in production.")
            if self.auto_create_tables:
                raise ValueError("Disable automatic schema creation in production; use migrations.")
        if self.access_token_minutes < 1 or self.refresh_token_days < 1:
            raise ValueError("Token lifetimes must be positive.")
        return self


settings = Settings()