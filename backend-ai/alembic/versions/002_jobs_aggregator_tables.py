"""Jobs aggregator: searches, runs, aggregated jobs, sources, board.

Revision ID: 002_jobs_aggregator_tables
Revises: 001_user_resume_columns
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_jobs_aggregator_tables"
down_revision: Union[str, None] = "001_user_resume_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_search_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=False),
        sa.Column("locations", sa.Text(), nullable=False),
        sa.Column("experience_levels", sa.Text(), nullable=False),
        sa.Column("employment_types", sa.Text(), nullable=False),
        sa.Column("remote_only", sa.Boolean(), nullable=False),
        sa.Column("selected_portals", sa.JSON(), nullable=False),
        sa.Column("schedule_enabled", sa.Boolean(), nullable=False),
        sa.Column("schedule_frequency", sa.String(length=16), nullable=True),
        sa.Column("schedule_time", sa.String(length=8), nullable=True),
        sa.Column("schedule_timezone", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_search_profiles_user_id", "job_search_profiles", ["user_id"])

    op.create_table(
        "job_search_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("search_profile_id", sa.Integer(), nullable=False),
        sa.Column("trigger_mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("scheduled_fire_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["search_profile_id"], ["job_search_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_search_runs_user_id", "job_search_runs", ["user_id"])
    op.create_index("ix_job_search_runs_search_profile_id", "job_search_runs", ["search_profile_id"])
    op.create_index("ix_job_search_runs_started_at", "job_search_runs", ["search_profile_id", "started_at"])
    op.create_index("ix_job_search_runs_scheduled_fire_at", "job_search_runs", ["scheduled_fire_at"])

    op.create_table(
        "aggregated_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("latest_run_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("company", sa.String(length=300), nullable=False),
        sa.Column("location", sa.String(length=300), nullable=False),
        sa.Column("salary_text", sa.String(length=300), nullable=False),
        sa.Column("posted_at", sa.String(length=64), nullable=True),
        sa.Column("description_snippet", sa.Text(), nullable=False),
        sa.Column("apply_url", sa.String(length=2000), nullable=False),
        sa.Column("canonical_apply_url", sa.String(length=2000), nullable=False),
        sa.Column("portal", sa.String(length=32), nullable=False),
        sa.Column("external_job_id", sa.String(length=255), nullable=True),
        sa.Column("dedupe_key", sa.String(length=512), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["latest_run_id"], ["job_search_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "dedupe_key", name="uq_aggregated_jobs_user_dedupe"),
    )
    op.create_index("ix_aggregated_jobs_user_id", "aggregated_jobs", ["user_id"])
    op.create_index("ix_aggregated_jobs_canonical_apply_url", "aggregated_jobs", ["canonical_apply_url"])
    op.create_index(
        "ix_aggregated_jobs_user_canonical_url",
        "aggregated_jobs",
        ["user_id", "canonical_apply_url"],
    )
    op.create_index("ix_aggregated_jobs_dedupe_key", "aggregated_jobs", ["dedupe_key"])
    op.create_index("ix_aggregated_jobs_portal", "aggregated_jobs", ["portal"])

    op.create_table(
        "job_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("portal", sa.String(length=32), nullable=False),
        sa.Column("source_url", sa.String(length=2000), nullable=False),
        sa.Column("apply_url", sa.String(length=2000), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("raw_meta", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["aggregated_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["job_search_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_sources_job_id", "job_sources", ["job_id"])
    op.create_index("ix_job_sources_run_id", "job_sources", ["run_id"])

    op.create_table(
        "job_board_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("follow_up_date", sa.String(length=32), nullable=True),
        sa.Column("recruiter_name", sa.String(length=200), nullable=False),
        sa.Column("recruiter_email", sa.String(length=255), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["job_id"], ["aggregated_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_job_board_user_job"),
    )
    op.create_index("ix_job_board_entries_user_id", "job_board_entries", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_job_board_entries_user_id", table_name="job_board_entries")
    op.drop_table("job_board_entries")
    op.drop_index("ix_job_sources_run_id", table_name="job_sources")
    op.drop_index("ix_job_sources_job_id", table_name="job_sources")
    op.drop_table("job_sources")
    op.drop_index("ix_aggregated_jobs_portal", table_name="aggregated_jobs")
    op.drop_index("ix_aggregated_jobs_dedupe_key", table_name="aggregated_jobs")
    op.drop_index("ix_aggregated_jobs_user_canonical_url", table_name="aggregated_jobs")
    op.drop_index("ix_aggregated_jobs_canonical_apply_url", table_name="aggregated_jobs")
    op.drop_index("ix_aggregated_jobs_user_id", table_name="aggregated_jobs")
    op.drop_table("aggregated_jobs")
    op.drop_index("ix_job_search_runs_scheduled_fire_at", table_name="job_search_runs")
    op.drop_index("ix_job_search_runs_started_at", table_name="job_search_runs")
    op.drop_index("ix_job_search_runs_search_profile_id", table_name="job_search_runs")
    op.drop_index("ix_job_search_runs_user_id", table_name="job_search_runs")
    op.drop_table("job_search_runs")
    op.drop_index("ix_job_search_profiles_user_id", table_name="job_search_profiles")
    op.drop_table("job_search_profiles")
