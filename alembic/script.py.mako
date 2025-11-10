"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}
# Import sqlmodel for SQLModel-specific types (AutoString, etc.)
import sqlmodel

# Helper function to create enum types safely (check if they exist first)
def create_enum_if_not_exists(enum_type):
    """Create a PostgreSQL enum type only if it doesn't already exist."""
    from sqlalchemy.dialects import postgresql
    if isinstance(enum_type, postgresql.ENUM):
        # Check if enum type exists
        conn = op.get_bind()
        enum_name = enum_type.name
        result = conn.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = :name)"
            ),
            {"name": enum_name}
        )
        exists = result.scalar()
        if not exists:
            enum_type.create(conn, checkfirst=False)
    elif hasattr(enum_type, 'create'):
        # For other enum types, use checkfirst
        conn = op.get_bind()
        enum_type.create(conn, checkfirst=True)

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade schema."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade schema."""
    ${downgrades if downgrades else "pass"}
