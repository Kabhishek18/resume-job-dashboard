"""Add results_wanted to job_search_profiles.

Revision ID: 003_job_profile_results_wanted
Revises: 002_jobs_aggregator_tables
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_job_profile_results_wanted"
down_revision: Union[str, None] = "002_jobs_aggregator_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_search_profiles",
        sa.Column("results_wanted", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("job_search_profiles", "results_wanted")
