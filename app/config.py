from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", env_file_encoding="utf-8")

    app_name: str = "AI CV Recruitment"
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "ai_cv_recruitment"
    db_user: str = "root"
    db_password: SecretStr = SecretStr("")
    gemini_api_key: SecretStr = SecretStr("")


settings = Settings()
