"""Private review ingestion and document provenance."""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "living_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("original_doi", sa.String(255), unique=True, nullable=False),
        sa.Column("original_title", sa.Text(), nullable=False),
        sa.Column("normalized_title", sa.Text()),
        sa.Column("original_authors", sa.JSON(), nullable=False),
        sa.Column("journal", sa.Text()),
        sa.Column("year", sa.Integer()),
        sa.Column("license", sa.String(100)),
        sa.Column("oa_url", sa.Text()),
        sa.Column("owner_curator_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("error_code", sa.String(100)),
        sa.Column("error_message", sa.Text()),
        sa.Column("source_key", sa.Text()),
        sa.Column("source_sha256", sa.String(64)),
        sa.Column("source_format", sa.String(10)),
        sa.Column("uploaded_key", sa.Text()),
        sa.Column("document", sa.JSON()),
        sa.Column("license_confirmed", sa.Boolean(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_living_reviews_normalized_title", "living_reviews", ["normalized_title"], unique=True
    )
    op.create_index("ix_living_reviews_owner_curator_id", "living_reviews", ["owner_curator_id"])


def downgrade():
    op.drop_table("living_reviews")
