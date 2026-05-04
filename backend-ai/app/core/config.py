from typing import List, Literal

from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

JWT_DEV_PLACEHOLDER = "dev-insecure-jwt-secret-change-in-production"
JWT_MIN_LENGTH_PRODUCTION = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: Literal["development", "production"] = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV"),
        description="production enforces a strong JWT_SECRET (see config validator).",
    )

    cors_origins_csv: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        validation_alias=AliasChoices("CORS_ORIGINS"),
        description="Comma-separated browser Origin values (scheme+host+port only, no path) for CORS.",
    )
    api_key_placeholder: str = ""
    debug: bool = False
    log_level: str = "INFO"

    tailoring_provider: Literal["stub", "llm"] = Field(
        default="stub",
        validation_alias=AliasChoices("TAILORING_PROVIDER"),
    )

    # OpenRouter — required when tailoring_provider==llm (validated below); ignored for stub.
    openrouter_api_key: str = Field(default="", validation_alias=AliasChoices("OPENROUTER_API_KEY"))
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias=AliasChoices("OPENROUTER_BASE_URL"),
    )
    openrouter_primary_model: str = Field(
        default="",
        validation_alias=AliasChoices("OPENROUTER_PRIMARY_MODEL"),
    )
    openrouter_fallback_models_csv: str = Field(
        default="",
        validation_alias=AliasChoices("OPENROUTER_FALLBACK_MODELS"),
    )
    openrouter_timeout_seconds: float = Field(
        default=90.0,
        validation_alias=AliasChoices("OPENROUTER_TIMEOUT_SECONDS"),
    )
    openrouter_http_referer: str = Field(
        default="",
        validation_alias=AliasChoices("OPENROUTER_HTTP_REFERER"),
    )
    openrouter_app_title: str = Field(
        default="",
        validation_alias=AliasChoices("OPENROUTER_APP_TITLE"),
    )

    database_url: str = "sqlite:///./data/app.db"
    jwt_secret: str = Field(
        default=JWT_DEV_PLACEHOLDER,
        description="HS256 signing secret; must be strong when APP_ENV=production.",
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # Password reset + mail (provider-agnostic; see app.services.mail)
    frontend_base_url: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("FRONTEND_BASE_URL", "APP_PUBLIC_ORIGIN"),
        description="Browser origin for reset links (no trailing path).",
    )
    password_reset_token_ttl_minutes: int = Field(
        default=60,
        ge=1,
        le=60 * 24 * 14,
        validation_alias=AliasChoices("PASSWORD_RESET_TOKEN_TTL_MINUTES"),
    )
    password_reset_pepper: str = Field(
        default="",
        validation_alias=AliasChoices("PASSWORD_RESET_PEPPER"),
        description="Optional extra secret for token hashing; defaults to JWT_SECRET when empty.",
    )
    mail_transport: Literal["noop", "console", "smtp"] = Field(
        default="noop",
        validation_alias=AliasChoices("MAIL_TRANSPORT"),
    )
    mail_from: str = Field(default="", validation_alias=AliasChoices("MAIL_FROM"))
    mail_smtp_host: str = Field(default="", validation_alias=AliasChoices("MAIL_SMTP_HOST"))
    mail_smtp_port: int = Field(default=587, validation_alias=AliasChoices("MAIL_SMTP_PORT"))
    mail_smtp_use_tls: bool = Field(default=True, validation_alias=AliasChoices("MAIL_SMTP_USE_TLS"))
    mail_smtp_username: str = Field(default="", validation_alias=AliasChoices("MAIL_SMTP_USERNAME"))
    mail_smtp_password: str = Field(default="", validation_alias=AliasChoices("MAIL_SMTP_PASSWORD"))

    # When false, skip alembic in FastAPI lifespan (run `alembic upgrade head` in deploy/release instead).
    run_migrations_on_startup: bool = Field(
        default=True,
        validation_alias=AliasChoices("RUN_MIGRATIONS_ON_STARTUP"),
    )
    # When false, APScheduler is not started in the web process (use single worker if true).
    enable_job_scheduler: bool = Field(
        default=True,
        validation_alias=AliasChoices("ENABLE_JOB_SCHEDULER"),
    )

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

    @field_validator("mail_transport", mode="before")
    @classmethod
    def _normalize_mail_transport(cls, v: object) -> object:
        if isinstance(v, str):
            x = v.strip().lower()
            if x in ("none", "off", "disabled"):
                return "noop"
            return x
        return v

    @model_validator(mode="after")
    def _jwt_strong_in_production(self) -> "Settings":
        if self.app_env != "production":
            return self
        secret = (self.jwt_secret or "").strip()
        if (
            not secret
            or secret == JWT_DEV_PLACEHOLDER
            or len(secret) < JWT_MIN_LENGTH_PRODUCTION
        ):
            raise ValueError(
                "APP_ENV=production requires JWT_SECRET to be a random string of at least "
                f"{JWT_MIN_LENGTH_PRODUCTION} characters (not the dev placeholder). "
                "Generate one for the API host only; never commit it."
            )
        return self

    @model_validator(mode="after")
    def _openrouter_required_for_llm_tailoring(self) -> "Settings":
        if self.tailoring_provider != "llm":
            return self
        if not (self.openrouter_api_key or "").strip():
            raise ValueError("TAILORING_PROVIDER=llm requires OPENROUTER_API_KEY.")
        if not (self.openrouter_primary_model or "").strip():
            raise ValueError("TAILORING_PROVIDER=llm requires OPENROUTER_PRIMARY_MODEL.")
        return self

    @computed_field
    @property
    def cors_origins(self) -> List[str]:
        return [x.strip() for x in self.cors_origins_csv.split(",") if x.strip()]

    @computed_field
    @property
    def frontend_origin_normalized(self) -> str:
        return (self.frontend_base_url or "").strip().rstrip("/")

    @computed_field
    @property
    def openrouter_fallback_models(self) -> List[str]:
        return [x.strip() for x in self.openrouter_fallback_models_csv.split(",") if x.strip()]

    @computed_field
    @property
    def openrouter_model_chain(self) -> List[str]:
        """Primary model first, then fallbacks; duplicates removed preserving order."""
        primary = (self.openrouter_primary_model or "").strip()
        if not primary:
            return []
        seen: set[str] = set()
        out: List[str] = []
        for m in [primary, *self.openrouter_fallback_models]:
            mid = (m or "").strip()
            if not mid or mid in seen:
                continue
            seen.add(mid)
            out.append(mid)
        return out


settings = Settings()
