"""create holiday_items

Revision ID: 0001_create_holiday_items
Revises:
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_create_holiday_items"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "holiday_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
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
    )

    op.create_index("ix_holiday_items_title", "holiday_items", ["title"])
    op.create_index("ix_holiday_items_status", "holiday_items", ["status"])
    op.create_index("ix_holiday_items_deleted_at", "holiday_items", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_holiday_items_deleted_at", table_name="holiday_items")
    op.drop_index("ix_holiday_items_status", table_name="holiday_items")
    op.drop_index("ix_holiday_items_title", table_name="holiday_items")
    op.drop_table("holiday_items")