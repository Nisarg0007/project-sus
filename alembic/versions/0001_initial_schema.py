"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-01

Creates the complete initial schema:
  - investigation_runs
  - persisted_incidents
  - incident_status_history

With all columns, constraints, indexes, and foreign keys.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables from scratch."""
    # investigation_runs
    op.create_table(
        "investigation_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("investigation_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("transactions_path", sa.String(length=512), nullable=False),
        sa.Column("window_labels_path", sa.String(length=512), nullable=False),
        sa.Column("model_path", sa.String(length=512), nullable=True),
        sa.Column("z_threshold", sa.Float(), nullable=False),
        sa.Column("min_history_days", sa.Integer(), nullable=False),
        sa.Column("merchant_filter", sa.String(length=128), nullable=True),
        sa.Column("total_results", sa.Integer(), nullable=False),
        sa.Column("spikes_detected", sa.Integer(), nullable=False),
        sa.Column("fraud_incidents", sa.Integer(), nullable=False),
        sa.Column("organic_incidents", sa.Integer(), nullable=False),
        sa.Column("review_required", sa.Integer(), nullable=False),
        sa.Column("baseline_windows", sa.Integer(), nullable=False),
        sa.Column("spike_rate", sa.Float(), nullable=False),
        sa.Column("processing_note", sa.Text(), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("investigation_id"),
    )
    op.create_index(
        "ix_investigation_runs_investigation_id",
        "investigation_runs",
        ["investigation_id"],
        unique=True,
    )

    # persisted_incidents
    op.create_table(
        "persisted_incidents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("investigation_run_id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.String(length=128), nullable=False),
        sa.Column("merchant_id", sa.String(length=128), nullable=False),
        sa.Column("date", sa.String(length=16), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("classification", sa.String(length=32), nullable=False),
        sa.Column("predicted_cause", sa.String(length=256), nullable=True),
        sa.Column("fraud_probability", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("confidence_band", sa.String(length=32), nullable=False),
        sa.Column("anomaly_score", sa.Float(), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("anomaly_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("top_signals_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("recommended_action", sa.Text(), nullable=False, server_default=""),
        sa.Column("workflow_status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("assigned_analyst", sa.String(length=128), nullable=True),
        sa.Column("analyst_notes", sa.Text(), nullable=True),
        sa.Column("resolution", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["investigation_run_id"],
            ["investigation_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_persisted_incidents_investigation_run_id",
        "persisted_incidents",
        ["investigation_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_persisted_incidents_incident_id",
        "persisted_incidents",
        ["incident_id"],
        unique=False,
    )
    op.create_index(
        "ix_persisted_incidents_merchant_id",
        "persisted_incidents",
        ["merchant_id"],
        unique=False,
    )
    op.create_index(
        "ix_persisted_incidents_severity",
        "persisted_incidents",
        ["severity"],
        unique=False,
    )
    op.create_index(
        "ix_persisted_incidents_classification",
        "persisted_incidents",
        ["classification"],
        unique=False,
    )
    op.create_index(
        "ix_persisted_incidents_workflow_status",
        "persisted_incidents",
        ["workflow_status"],
        unique=False,
    )
    op.create_index(
        "ix_incidents_merchant_date",
        "persisted_incidents",
        ["merchant_id", "date"],
        unique=False,
    )
    op.create_index(
        "ix_incidents_classification_severity",
        "persisted_incidents",
        ["classification", "severity"],
        unique=False,
    )

    # incident_status_history
    op.create_table(
        "incident_status_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("old_status", sa.String(length=32), nullable=False),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column("changed_by", sa.String(length=128), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["persisted_incidents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_incident_status_history_incident_id",
        "incident_status_history",
        ["incident_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("incident_status_history")
    op.drop_table("persisted_incidents")
    op.drop_table("investigation_runs")
