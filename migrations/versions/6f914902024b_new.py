"""new

Revision ID: 6f914902024b
Revises: 81673dbc2f34
Create Date: 2025-10-27 20:39:12.860777

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '6f914902024b'
down_revision: Union[str, Sequence[str], None] = '81673dbc2f34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    
    # Create ENUM types
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE verification_method_enum AS ENUM ('oauth', 'code');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE verification_status_enum AS ENUM ('pending', 'verified', 'failed', 'unverified');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE attempt_method_enum AS ENUM ('oauth', 'code');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE attempt_status_enum AS ENUM ('pending', 'verified', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    # Create sample_reports table
    op.create_table('sample_reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('report_name', sa.String(length=255), nullable=False),
        sa.Column('video_url', sa.String(length=500), nullable=False),
        sa.Column('analysis_data', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create verification_attempts table using raw SQL to avoid enum creation issues
    conn.execute(sa.text("""
        CREATE TABLE verification_attempts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            channel_url VARCHAR(500) NOT NULL,
            verification_code VARCHAR(100) NOT NULL,
            verification_method attempt_method_enum NOT NULL,
            status attempt_status_enum,
            attempts INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE,
            verified_at TIMESTAMP WITH TIME ZONE
        )
    """))
    
    # Add columns to users table using raw SQL
    conn.execute(sa.text("ALTER TABLE users ADD COLUMN youtube_channel_id VARCHAR(100)"))
    conn.execute(sa.text("ALTER TABLE users ADD COLUMN verification_method verification_method_enum"))
    conn.execute(sa.text("ALTER TABLE users ADD COLUMN verification_status verification_status_enum"))
    conn.execute(sa.text("ALTER TABLE users ADD COLUMN verification_date TIMESTAMP WITH TIME ZONE"))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    
    # Drop columns
    conn.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS verification_date"))
    conn.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS verification_status"))
    conn.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS verification_method"))
    conn.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS youtube_channel_id"))
    
    # Drop tables
    op.drop_table('verification_attempts')
    op.drop_table('sample_reports')
    
    # Drop ENUM types
    conn.execute(sa.text("DROP TYPE IF EXISTS verification_method_enum CASCADE"))
    conn.execute(sa.text("DROP TYPE IF EXISTS verification_status_enum CASCADE"))
    conn.execute(sa.text("DROP TYPE IF EXISTS attempt_method_enum CASCADE"))
    conn.execute(sa.text("DROP TYPE IF EXISTS attempt_status_enum CASCADE"))