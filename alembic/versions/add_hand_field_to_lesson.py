"""Add hand field to lesson

Revision ID: add_hand_to_lesson
Revises: dbc24f3df739
Create Date: 2026-04-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_hand_to_lesson'
down_revision = 'dbc24f3df739'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('lesson', sa.Column('hand', sa.String(), nullable=False, server_default='right'))


def downgrade() -> None:
    op.drop_column('lesson', 'hand')
