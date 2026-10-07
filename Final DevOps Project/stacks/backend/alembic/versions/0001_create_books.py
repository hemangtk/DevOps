"""create books table

Revision ID: 0001
Revises:
Create Date: 2026-10-07

Name: Hemang | Enrollment number: 24bcs10209
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("author", sa.String(length=120), nullable=False),
        sa.Column("isbn", sa.String(length=17), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="AVAILABLE"),
        sa.Column("borrower", sa.String(length=120), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_books_id", "books", ["id"])
    # one physical copy per ISBN in this catalogue - enforced by the DB, not
    # only by the API, so a second writer cannot slip a duplicate past it
    op.create_unique_constraint("uq_books_isbn", "books", ["isbn"])
    op.create_index("ix_books_isbn", "books", ["isbn"])


def downgrade() -> None:
    op.drop_index("ix_books_isbn", table_name="books")
    op.drop_constraint("uq_books_isbn", "books", type_="unique")
    op.drop_index("ix_books_id", table_name="books")
    op.drop_table("books")
