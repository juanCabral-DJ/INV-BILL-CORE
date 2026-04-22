"""unificando nombre y username de usuarios

Revision ID: f6a7b8c9d0e1
Revises: b2c3d4e5f6a7
Create Date: 2026-04-16 15:40:00

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE usuarios
        SET nombre = username
        WHERE nombre IS DISTINCT FROM username
        """
    )


def downgrade() -> None:
    pass
