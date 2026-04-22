"""merge heads

Revision ID: f61b1628866b
Revises: 9354bb62dce8, 9d2e6b2d1f3a
Create Date: 2026-04-22 13:47:30.714727

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f61b1628866b'
down_revision: Union[str, Sequence[str], None] = ('9354bb62dce8', '9d2e6b2d1f3a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
