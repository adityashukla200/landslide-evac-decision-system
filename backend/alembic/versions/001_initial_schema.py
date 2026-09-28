"""Initial database schema for EWS

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-28 18:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # Define geometry type conditionally
    if is_postgres:
        import geoalchemy2
        geom_type = geoalchemy2.Geometry(geometry_type="GEOMETRY", srid=4326)
    else:
        geom_type = sa.Text()

    # 1. Villages
    op.create_table(
        "villages",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("district", sa.String(length=64), nullable=False),
        sa.Column("geometry", geom_type, nullable=True),
        sa.Column("population", sa.Integer(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("elevation", sa.Float(), nullable=False),
    )
    op.create_index("ix_villages_id", "villages", ["id"])
    op.create_index("ix_villages_name", "villages", ["name"])
    op.create_index("ix_villages_district", "villages", ["district"])

    # 2. Sensors
    op.create_table(
        "sensors",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("village_id", sa.String(length=64), sa.ForeignKey("villages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("last_seen", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_sensors_id", "sensors", ["id"])
    op.create_index("ix_sensors_village_id", "sensors", ["village_id"])

    # 3. Observations
    op.create_table(
        "observations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("time", sa.DateTime(), nullable=False),
        sa.Column("sensor_id", sa.String(length=64), sa.ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variable", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
    )
    op.create_index("ix_observations_time", "observations", ["time"])
    op.create_index("ix_observations_sensor_id", "observations", ["sensor_id"])

    # 4. Risk Assessments
    op.create_table(
        "risk_assessments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("time", sa.DateTime(), nullable=False),
        sa.Column("village_id", sa.String(length=64), sa.ForeignKey("villages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("lower", sa.Float(), nullable=False),
        sa.Column("upper", sa.Float(), nullable=False),
        sa.Column("tier", sa.String(length=16), nullable=False),
        sa.Column("explanation_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_risk_assessments_time", "risk_assessments", ["time"])
    op.create_index("ix_risk_assessments_village_id", "risk_assessments", ["village_id"])

    # 5. Alerts
    op.create_table(
        "alerts",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("village_id", sa.String(length=64), sa.ForeignKey("villages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tier", sa.String(length=16), nullable=False),
        sa.Column("message", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_alerts_id", "alerts", ["id"])
    op.create_index("ix_alerts_village_id", "alerts", ["village_id"])

    # 6. Recipients
    op.create_table(
        "recipients",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("village_id", sa.String(length=64), sa.ForeignKey("villages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column("vulnerable_flag", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("volunteer_id", sa.String(length=64), sa.ForeignKey("recipients.id"), nullable=True),
    )
    op.create_index("ix_recipients_id", "recipients", ["id"])
    op.create_index("ix_recipients_village_id", "recipients", ["village_id"])

    # 7. Alert Deliveries
    op.create_table(
        "alert_deliveries",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("alert_id", sa.String(length=64), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_id", sa.String(length=64), sa.ForeignKey("recipients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("acked_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_alert_deliveries_id", "alert_deliveries", ["id"])
    op.create_index("ix_alert_deliveries_alert_id", "alert_deliveries", ["alert_id"])
    op.create_index("ix_alert_deliveries_recipient_id", "alert_deliveries", ["recipient_id"])

    # 8. Shelters
    op.create_table(
        "shelters",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("geometry", geom_type, nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("village_id", sa.String(length=64), sa.ForeignKey("villages.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_index("ix_shelters_id", "shelters", ["id"])
    op.create_index("ix_shelters_village_id", "shelters", ["village_id"])

    # 9. Routes
    op.create_table(
        "routes",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("from_village", sa.String(length=64), sa.ForeignKey("villages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_shelter", sa.String(length=64), sa.ForeignKey("shelters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("length_m", sa.Float(), nullable=False),
        sa.Column("est_walk_minutes", sa.Float(), nullable=False),
        sa.Column("cut_risk", sa.Float(), nullable=False, server_default=sa.text("0.0")),
    )
    op.create_index("ix_routes_id", "routes", ["id"])
    op.create_index("ix_routes_from_village", "routes", ["from_village"])
    op.create_index("ix_routes_to_shelter", "routes", ["to_shelter"])


def downgrade() -> None:
    op.drop_table("routes")
    op.drop_table("shelters")
    op.drop_table("alert_deliveries")
    op.drop_table("recipients")
    op.drop_table("alerts")
    op.drop_table("risk_assessments")
    op.drop_table("observations")
    op.drop_table("sensors")
    op.drop_table("villages")
