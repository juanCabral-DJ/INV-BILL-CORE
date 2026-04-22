"""agregando pago y cambio a facturas

Revision ID: a7c5e2d1f9b3
Revises: d1f3c5b7a9e2
Create Date: 2026-04-20 11:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7c5e2d1f9b3"
down_revision: Union[str, Sequence[str], None] = "d1f3c5b7a9e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "facturas",
        sa.Column("monto_pagado", sa.Numeric(precision=18, scale=2), nullable=True, server_default=sa.text("0")),
    )
    op.add_column(
        "facturas",
        sa.Column("cambio_devuelto", sa.Numeric(precision=18, scale=2), nullable=True, server_default=sa.text("0")),
    )
    op.execute("UPDATE facturas SET monto_pagado = monto_total WHERE monto_pagado IS NULL OR monto_pagado = 0")
    op.execute("UPDATE facturas SET cambio_devuelto = 0 WHERE cambio_devuelto IS NULL")
    op.alter_column("facturas", "monto_pagado", nullable=False, server_default=None)
    op.alter_column("facturas", "cambio_devuelto", nullable=False, server_default=None)


def downgrade() -> None:
    op.drop_column("facturas", "cambio_devuelto")
    op.drop_column("facturas", "monto_pagado")
