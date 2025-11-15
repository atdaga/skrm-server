"""root_user

Revision ID: 9609fa391edc
Revises: e3a2157c0a5e
Create Date: 2025-11-09 19:16:56.444747

"""
from collections.abc import Sequence

from alembic import op

# Import sqlmodel for SQLModel-specific types (AutoString, etc.)

# revision identifiers, used by Alembic.
revision: str = '9609fa391edc'
down_revision: str | Sequence[str] | None = 'e3a2157c0a5e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Insert root user
    op.execute("""
        INSERT INTO k_principal (id,"scope",username,primary_email,primary_email_verified,primary_phone,primary_phone_verified,human,enabled,time_zone,name_prefix,first_name,middle_name,last_name,name_suffix,display_name,default_locale,system_role,meta,deleted,created,created_by,last_modified,last_modified_by)
        VALUES ('00000000-0000-0000-0000-000000000000'::uuid,'global','root','root@global.scope',false,NULL,false,true,true,'UTC',NULL,'Root',NULL,'User',NULL,'Root User','en','systemRoot','{}',false,'2025-10-05 21:35:05.226091','00000000-0000-0000-0000-000000000000'::uuid,'2025-10-05 21:35:05.226091','00000000-0000-0000-0000-000000000000'::uuid)
    """)

    # Insert root user identity (password: P@ssword12)
    op.execute("""
        INSERT INTO k_principal_identity (id,principal_id,"password",public_key,device_id,expires,details,created,created_by,last_modified,last_modified_by)
        VALUES ('00000000-0000-0000-0000-000000000000'::uuid,'00000000-0000-0000-0000-000000000000'::uuid,'$2b$12$rdK6qPYTy0OEmjrHSlqsv.GSkqqi2gcJJyMIsMma.SeQS1HwqG002',NULL,NULL,NULL,'{}','2025-10-05 21:38:16.33076','00000000-0000-0000-0000-000000000000'::uuid,'2025-10-05 21:38:16.33076','00000000-0000-0000-0000-000000000000'::uuid)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove root user identity
    op.execute("DELETE FROM k_principal_identity WHERE id = '00000000-0000-0000-0000-000000000000'")

    # Remove root user
    op.execute("DELETE FROM k_principal WHERE id = '00000000-0000-0000-0000-000000000000'")
