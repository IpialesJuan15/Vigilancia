"""F0 users, single-use tokens and append-only audit log."""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def stamps():
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "users",
        *stamps(),
        sa.Column("email", sa.String(254), unique=True),
        sa.Column("password_hash", sa.String(512)),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("orcid_id", sa.String(19), unique=True),
        sa.Column("institution", sa.String(250)),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("notification_prefs", sa.JSON(), nullable=False),
        sa.Column("session_version", sa.Integer(), nullable=False),
        sa.CheckConstraint("role in ('admin','curator','subscriber')"),
    )
    op.create_table(
        "auth_tokens",
        *stamps(),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("digest", sa.String(64), unique=True, nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])
    op.create_table(
        "audit_log",
        *stamps(),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(36)),
        sa.Column("before", sa.JSON()),
        sa.Column("after", sa.JSON()),
    )
    op.execute("""CREATE FUNCTION forbid_audit_changes() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'audit_log is append-only'; END;
        $$ LANGUAGE plpgsql""")
    op.execute("""CREATE TRIGGER audit_immutable BEFORE UPDATE OR DELETE OR TRUNCATE
        ON audit_log FOR EACH STATEMENT EXECUTE FUNCTION forbid_audit_changes()""")


def downgrade():
    op.drop_table("audit_log")
    op.execute("DROP FUNCTION forbid_audit_changes()")
    op.drop_table("auth_tokens")
    op.drop_table("users")
