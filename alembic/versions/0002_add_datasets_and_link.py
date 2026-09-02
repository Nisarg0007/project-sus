"""add datasets table and link investigation_runs to datasets

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-02

Adds:
  - datasets table (metadata for uploaded transaction CSVs)
  - dataset_id column on investigation_runs (nullable FK to datasets.dataset_id)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create datasets table
    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("original_filename", sa.String(length=256), nullable=False),
        sa.Column("stored_path", sa.String(length=512), nullable=False),
        sa.Column("data_source_type", sa.String(length=32), nullable=False, server_default="csv"),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("merchant_count", sa.Integer(), nullable=True),
        sa.Column("min_transaction_date", sa.String(length=32), nullable=True),
        sa.Column("max_transaction_date", sa.String(length=32), nullable=True),
        sa.Column("validation_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("validation_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_id"),
    )
    op.create_index(
        "ix_datasets_dataset_id",
        "datasets",
        ["dataset_id"],
        unique=True,
    )

    # Add dataset_id to investigation_runs
    with op.batch_alter_table("investigation_runs") as batch_op:
        batch_op.add_column(
            sa.Column("dataset_id", sa.String(length=64), nullable=True)
        )
        batch_op.create_index(
            "ix_investigation_runs_dataset_id",
            ["dataset_id"],
            unique=False,
        )


def downgrade() -> None:
    # Remove dataset_id from investigation_runs
    with op.batch_alter_table("investigation_runs") as batch_op:
        batch_op.drop_index("ix_investigation_runs_dataset_id")
        batch_op.drop_column("dataset_id")

    # Drop datasets table
    op.drop_index("ix_datasets_dataset_id", table_name="datasets")
    op.drop_table("datasets")
