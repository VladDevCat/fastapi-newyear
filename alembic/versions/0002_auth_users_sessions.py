"""add users auth and ownership

Revision ID: 0002_auth_users_sessions
Revises: 0001_create_holiday_items
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_auth_users_sessions"
down_revision = "0001_create_holiday_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("password_salt", sa.String(length=64), nullable=True),
        sa.Column("yandex_id", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("phone", name="uq_users_phone"),
        sa.UniqueConstraint("yandex_id", name="uq_users_yandex_id"),
    )

    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_phone", "users", ["phone"])
    op.create_index("ix_users_yandex_id", "users", ["yandex_id"])
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])

    op.create_table(
        "session_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_type", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_session_tokens_token_hash"),
    )

    op.create_index("ix_session_tokens_session_id", "session_tokens", ["session_id"])
    op.create_index("ix_session_tokens_user_id", "session_tokens", ["user_id"])
    op.create_index("ix_session_tokens_token_type", "session_tokens", ["token_type"])
    op.create_index("ix_session_tokens_expires_at", "session_tokens", ["expires_at"])
    op.create_index("ix_session_tokens_is_revoked", "session_tokens", ["is_revoked"])

    op.add_column(
        "holiday_items",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_holiday_items_owner_id_users",
        "holiday_items",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_holiday_items_owner_id", "holiday_items", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_holiday_items_owner_id", table_name="holiday_items")
    op.drop_constraint("fk_holiday_items_owner_id_users", "holiday_items", type_="foreignkey")
    op.drop_column("holiday_items", "owner_id")

    op.drop_index("ix_session_tokens_is_revoked", table_name="session_tokens")
    op.drop_index("ix_session_tokens_expires_at", table_name="session_tokens")
    op.drop_index("ix_session_tokens_token_type", table_name="session_tokens")
    op.drop_index("ix_session_tokens_user_id", table_name="session_tokens")
    op.drop_index("ix_session_tokens_session_id", table_name="session_tokens")
    op.drop_table("session_tokens")

    op.drop_index("ix_users_deleted_at", table_name="users")
    op.drop_index("ix_users_yandex_id", table_name="users")
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")