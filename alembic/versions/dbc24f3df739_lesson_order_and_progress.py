"""lesson order and progress

Revision ID: dbc24f3df739
Revises: f61b1628866b
Create Date: 2026-04-22 13:48:28.851152

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dbc24f3df739"
down_revision: Union[str, Sequence[str], None] = "f61b1628866b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["lesson_id"], ["lesson.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson"),
    )
    op.create_index(
        op.f("ix_lesson_progress_id"), "lesson_progress", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_lesson_progress_lesson_id"),
        "lesson_progress",
        ["lesson_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lesson_progress_user_id"),
        "lesson_progress",
        ["user_id"],
        unique=False,
    )

    # Backfill existing lessons so we can make the column NOT NULL.
    op.add_column("lesson", sa.Column("order_in_topic", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE lesson l
        SET order_in_topic = s.rn
        FROM (
            SELECT id, row_number() OVER (PARTITION BY topic_id ORDER BY id) AS rn
            FROM lesson
        ) s
        WHERE l.id = s.id
        """
    )
    op.alter_column("lesson", "order_in_topic", nullable=False)
    op.create_index(
        op.f("ix_lesson_order_in_topic"), "lesson", ["order_in_topic"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_lesson_order_in_topic"), table_name="lesson")
    op.drop_column("lesson", "order_in_topic")

    op.drop_index(op.f("ix_lesson_progress_user_id"), table_name="lesson_progress")
    op.drop_index(op.f("ix_lesson_progress_lesson_id"), table_name="lesson_progress")
    op.drop_index(op.f("ix_lesson_progress_id"), table_name="lesson_progress")
    op.drop_table("lesson_progress")
