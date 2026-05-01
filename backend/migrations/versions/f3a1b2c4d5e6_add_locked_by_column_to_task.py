"""add locked_by column to task

Revision ID: f3a1b2c4d5e6
Revises: ee7bf0b63d9a
Create Date: 2026-05-02 03:56:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a1b2c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'c092691f839f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add locked_by column to track which worker owns a task."""
    op.add_column('task', sa.Column('locked_by', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Remove locked_by column."""
    op.drop_column('task', 'locked_by')
