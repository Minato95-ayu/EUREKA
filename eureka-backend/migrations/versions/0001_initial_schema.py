"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-25
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "agent_conversations",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("experiment_id", sa.String()),
        sa.Column("user_id", sa.UUID()),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("agent_used", sa.ARRAY(sa.String())),
        sa.Column("agent_responses", sa.JSON()),
        sa.Column("unified_response", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_agent_conversations_experiment", "agent_conversations", ["experiment_id"])

    op.create_table(
        "research_papers",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("arxiv_id", sa.String(), unique=True),
        sa.Column("pubmed_id", sa.String(), unique=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("authors", sa.ARRAY(sa.Text())),
        sa.Column("abstract", sa.Text()),
        sa.Column("url", sa.String()),
        sa.Column("keywords", sa.ARRAY(sa.Text())),
        sa.Column("cached_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "agent_metrics",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("agent_name", sa.String(), nullable=False),
        sa.Column("request_type", sa.String()),
        sa.Column("response_time_ms", sa.Integer()),
        sa.Column("success", sa.Boolean()),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_agent_metrics_agent", "agent_metrics", ["agent_name"])

    op.create_table(
        "simulations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("experiment_id", sa.String()),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("type", sa.String()),
        sa.Column("status", sa.String()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_simulations_experiment", "simulations", ["experiment_id"])

    op.create_table(
        "simulation_particles",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("simulation_id", sa.String(), sa.ForeignKey("simulations.id", ondelete="CASCADE")),
        sa.Column("particle_type", sa.String()),
        sa.Column("position", sa.ARRAY(sa.Float())),
        sa.Column("velocity", sa.ARRAY(sa.Float())),
        sa.Column("mass", sa.Float()),
        sa.Column("charge", sa.Float()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_simulation_particles_simulation", "simulation_particles", ["simulation_id"])

    op.create_table(
        "simulation_results",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("simulation_id", sa.String(), sa.ForeignKey("simulations.id", ondelete="CASCADE")),
        sa.Column("trajectory", sa.JSON()),
        sa.Column("energies", sa.ARRAY(sa.Float())),
        sa.Column("final_energy", sa.Float()),
        sa.Column("simulation_time", sa.Float()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_simulation_results_simulation", "simulation_results", ["simulation_id"])

    op.create_table(
        "simulation_reactions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("simulation_id", sa.String(), sa.ForeignKey("simulations.id", ondelete="CASCADE")),
        sa.Column("reactants", sa.ARRAY(sa.Text())),
        sa.Column("products", sa.ARRAY(sa.Text())),
        sa.Column("energy_change", sa.Float()),
        sa.Column("feasible", sa.Boolean()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_simulation_reactions_simulation", "simulation_reactions", ["simulation_id"])

    op.create_table(
        "collaborations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("experiment_id", sa.String()),
        sa.Column("owner_id", sa.String()),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_public", sa.Boolean(), server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_collaborations_experiment", "collaborations", ["experiment_id"])

    op.create_table(
        "collaboration_members",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("collaboration_id", sa.String(), sa.ForeignKey("collaborations.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.String()),
        sa.Column("role", sa.String()),
        sa.Column("joined_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("collaboration_id", "user_id"),
    )
    op.create_index("idx_collaboration_members_user", "collaboration_members", ["user_id"])

    op.create_table(
        "comments",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("collaboration_id", sa.String(), sa.ForeignKey("collaborations.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.String()),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("line_number", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_comments_collaboration", "comments", ["collaboration_id"])

    op.create_table(
        "experiment_versions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("collaboration_id", sa.String(), sa.ForeignKey("collaborations.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.String()),
        sa.Column("data", sa.JSON()),
        sa.Column("message", sa.String()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_experiment_versions_collaboration", "experiment_versions", ["collaboration_id"])


def downgrade() -> None:
    op.drop_table("experiment_versions")
    op.drop_table("comments")
    op.drop_table("collaboration_members")
    op.drop_table("collaborations")
    op.drop_table("simulation_reactions")
    op.drop_table("simulation_results")
    op.drop_table("simulation_particles")
    op.drop_table("simulations")
    op.drop_table("agent_metrics")
    op.drop_table("research_papers")
    op.drop_table("agent_conversations")
