from typing import Literal, List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    api_key_placeholder: str = ""
    debug: bool = False
    log_level: str = "INFO"

    tailoring_provider: Literal["stub", "llm"] = "stub"

    database_url: str = "sqlite:///./data/app.db"
    jwt_secret: str = Field(
        default="dev-insecure-jwt-secret-change-in-production",
        description="HS256 signing secret; override in production.",
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # JobSpy (Indeed/Glassdoor country string, e.g. india, usa — see JobSpy Country.from_string)
    jobspy_country_indeed: str = "india"
    jobspy_results_wanted: int = 30
    # Optional HTTP proxy for JobSpy (helps when Indeed returns 403 from your IP). e.g. http://host:port
    jobspy_proxy: str = ""
    # Indeed is opt-in: many networks get HTTP 403. Set JOBSPY_RUN_INDEED=true in .env to scrape Indeed.
    jobspy_run_indeed: bool = False


settings = Settings()
