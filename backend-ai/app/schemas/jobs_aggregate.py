"""Pydantic models for jobs aggregation API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

PortalIdLiteral = str


class SearchProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    keywords: str = ""
    locations: str = ""
    experience_levels: str = ""
    employment_types: str = ""
    remote_only: bool = False
    selected_portals: List[str] = Field(default_factory=list)
    schedule_enabled: bool = False
    schedule_frequency: Optional[str] = None  # daily|weekly
    schedule_time: Optional[str] = None  # HH:MM
    schedule_timezone: Optional[str] = "UTC"


class SearchProfilePatch(BaseModel):
    name: Optional[str] = None
    keywords: Optional[str] = None
    locations: Optional[str] = None
    experience_levels: Optional[str] = None
    employment_types: Optional[str] = None
    remote_only: Optional[bool] = None
    selected_portals: Optional[List[str]] = None
    schedule_enabled: Optional[bool] = None
    schedule_frequency: Optional[str] = None
    schedule_time: Optional[str] = None
    schedule_timezone: Optional[str] = None


class SearchProfileApi(BaseModel):
    id: int
    user_id: int
    name: str
    keywords: str
    locations: str
    experience_levels: str
    employment_types: str
    remote_only: bool
    selected_portals: List[str]
    schedule_enabled: bool
    schedule_frequency: Optional[str]
    schedule_time: Optional[str]
    schedule_timezone: Optional[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class JobSearchRunApi(BaseModel):
    id: int
    user_id: int
    search_profile_id: int
    trigger_mode: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    summary_json: Dict[str, Any] = Field(default_factory=dict)
    scheduled_fire_at: Optional[datetime] = None


class AggregatedJobRowApi(BaseModel):
    id: int
    portal: str
    title: str
    company: str
    location: str
    posted_at: Optional[str]
    salary_text: str
    apply_url: str
    duplicate_count: int
    board_status: Optional[str] = None
    source_count: int = 1


class BoardEntryCreate(BaseModel):
    job_id: int


class BoardEntryPatch(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[str] = None
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    applied_at: Optional[datetime] = None


class BoardEntryApi(BaseModel):
    id: int
    user_id: int
    job_id: int
    status: str
    notes: str
    follow_up_date: Optional[str]
    recruiter_name: str
    recruiter_email: str
    applied_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    title: str = ""
    company: str = ""
    portal: str = ""
    apply_url: str = ""
