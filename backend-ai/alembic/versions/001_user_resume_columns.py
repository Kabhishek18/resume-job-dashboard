"""User resume columns; create users table or alter existing SQLite DB.

Revision ID: 001_user_resume_columns
Revises:
Create Date: 2026-05-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import inspect
from alembic import op

revision: str = "001_user_resume_columns"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("resume_text", sa.Text(), nullable=True),
            sa.Column("resume_updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)
        return

    cols = {c["name"] for c in inspector.get_columns("users")}
    if "resume_text" not in cols:
        op.add_column("users", sa.Column("resume_text", sa.Text(), nullable=True))
    if "resume_updated_at" not in cols:
        op.add_column(
            "users",
            sa.Column("resume_updated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "resume_text" in cols:
        op.drop_column("users", "resume_text")
    if "resume_updated_at" in cols:
        op.drop_column("users", "resume_updated_at")
