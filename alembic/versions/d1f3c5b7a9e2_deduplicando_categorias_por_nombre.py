"""deduplicando categorias por nombre

Revision ID: d1f3c5b7a9e2
Revises: c9d8e7f6a5b4
Create Date: 2026-04-16 10:20:00

"""
from typing import Sequence, Union

from alembic import op


revision: str = "d1f3c5b7a9e2"
down_revision: Union[str, Sequence[str], None] = "c9d8e7f6a5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        WITH categorias_ranked AS (
            SELECT
                id,
                nombre,
                BTRIM(nombre) AS nombre_limpio,
                LOWER(BTRIM(nombre)) AS nombre_normalizado,
                FIRST_VALUE(id) OVER (
                    PARTITION BY LOWER(BTRIM(nombre))
                    ORDER BY id
                ) AS categoria_principal_id,
                ROW_NUMBER() OVER (
                    PARTITION BY LOWER(BTRIM(nombre))
                    ORDER BY id
                ) AS fila
            FROM categorias
        )
        UPDATE productos AS p
        SET categoria_id = cr.categoria_principal_id
        FROM categorias_ranked AS cr
        WHERE p.categoria_id = cr.id
          AND cr.fila > 1
          AND p.categoria_id <> cr.categoria_principal_id
        """
    )

    op.execute(
        """
        WITH categorias_ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY LOWER(BTRIM(nombre))
                    ORDER BY id
                ) AS fila
            FROM categorias
        )
        DELETE FROM categorias AS c
        USING categorias_ranked AS cr
        WHERE c.id = cr.id
          AND cr.fila > 1
        """
    )

    op.execute(
        """
        UPDATE categorias
        SET nombre = BTRIM(nombre)
        WHERE nombre <> BTRIM(nombre)
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_categorias_nombre_normalizado
        ON categorias (LOWER(BTRIM(nombre)))
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_categorias_nombre_normalizado")
