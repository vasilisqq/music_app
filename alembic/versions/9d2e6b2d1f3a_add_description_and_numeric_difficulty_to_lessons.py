"""add description and numeric difficulty to lessons

Revision ID: 9d2e6b2d1f3a
Revises: c3bb436bece8
Create Date: 2026-04-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9d2e6b2d1f3a"
down_revision: Union[str, Sequence[str], None] = "c3bb436bece8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("lesson", sa.Column("description", sa.String(), nullable=False, server_default=""))
    op.alter_column(
        "lesson",
        "difficult",
        existing_type=sa.String(),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="difficult::integer",
    )
    op.alter_column("lesson", "description", server_default=None)


def downgrade() -> None:
    op.alter_column(
        "lesson",
        "difficult",
        existing_type=sa.Integer(),
        type_=sa.String(),
        existing_nullable=False,
        postgresql_using="difficult::text",
    )
    op.drop_column("lesson", "description")
