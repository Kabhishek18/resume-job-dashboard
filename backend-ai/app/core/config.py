from typing import Literal, List

from pydantic import AliasChoices, Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    cors_origins_csv: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        validation_alias=AliasChoices("CORS_ORIGINS"),
        description="Comma-separated browser Origin values (scheme+host+port only, no path) for CORS.",
    )
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
    # ZipRecruiter is opt-in for the same reason as Indeed.
    jobspy_run_zip_recruiter: bool = False

    # Indeed: direct HTML SERP (optional fallback when JobSpy Indeed fails); only if user opted into Indeed.
    indeed_html_fallback_enabled: bool = True
    indeed_html_max_listings: int = 18
    indeed_html_from_age_days: int = 14

    # LinkedIn guest fetch (httpx + HTML cards): no JobSpy, ignores JOBSPY_PROXY.
    linkedin_guest_enabled: bool = True
    # If true, skip JobSpy for LinkedIn and use only the guest path (useful when proxy/JobSpy breaks LI).
    linkedin_use_guest_instead_of_jobspy: bool = False

    # Firecrawl (optional): Naukri search pages are often JS-heavy; used when direct HTML has no listing links.
    firecrawl_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("FIRECRAWL_API_KEY", "FireCrawl_API_KEY"),
    )
    firecrawl_api_url: str = "https://api.firecrawl.dev"
    firecrawl_enabled: bool = True  # Set FIRECRAWL_ENABLED=false to skip even when key is set

    # Naukri: HTML + optional Firecrawl (never passed to python-jobspy).
    naukri_html_enabled: bool = True
    naukri_max_listings: int = 18
    naukri_http_user_agent: str = ""

    @field_validator("naukri_max_listings", mode="before")
    @classmethod
    def _clamp_naukri_max(cls, v: object) -> int:
        try:
            n = int(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            n = 18
        return max(1, min(100, n))

    @field_validator("indeed_html_max_listings", mode="before")
    @classmethod
    def _clamp_indeed_html_max(cls, v: object) -> int:
        try:
            n = int(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            n = 18
        return max(1, min(50, n))

    @field_validator("indeed_html_from_age_days", mode="before")
    @classmethod
    def _clamp_indeed_fromage(cls, v: object) -> int:
        try:
            n = int(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            n = 14
        return max(1, min(30, n))

    @computed_field
    @property
    def cors_origins(self) -> List[str]:
        return [x.strip() for x in self.cors_origins_csv.split(",") if x.strip()]


settings = Settings()
