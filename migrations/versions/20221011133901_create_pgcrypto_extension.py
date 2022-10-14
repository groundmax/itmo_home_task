"""create_pgcrypto_extension

Revision ID: 3d5ad862d83d
Revises:
Create Date: 2022-10-11 13:39:01.367256

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "3d5ad862d83d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pgcrypto;")
