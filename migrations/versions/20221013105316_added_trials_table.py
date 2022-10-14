"""Added trials table

Revision ID: 01d29d9e5f5a
Revises: 19ccc11cccc6
Create Date: 2022-10-13 10:53:16.037821

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "01d29d9e5f5a"
down_revision = "19ccc11cccc6"
branch_labels = None
depends_on = None

SERVER_UUID = sa.text("gen_random_uuid()")


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "trials",
        sa.Column("trial_id", postgresql.UUID(), nullable=False, server_default=SERVER_UUID),
        sa.Column("model_id", postgresql.UUID(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("finished_at", postgresql.TIMESTAMP(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("waiting", "started", "success", "failed", name="trial_status_enum"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["models.model_id"],
        ),
        sa.PrimaryKeyConstraint("trial_id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("trials")
    # ### end Alembic commands ###
    op.execute("DROP TYPE trial_status_enum")
