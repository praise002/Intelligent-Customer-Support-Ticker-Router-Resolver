"""Add missing issue types

Revision ID: ab0d1f70c669
Revises: 3354a247c318
Create Date: 2026-03-22 19:52:09.741839

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ab0d1f70c669"
down_revision: Union[str, Sequence[str], None] = "3354a247c318"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
