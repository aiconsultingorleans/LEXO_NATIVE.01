"""Initial migration: users and documents tables

Revision ID: b342af89685a
Revises: 
Create Date: 2025-07-23 16:19:05.474176

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b342af89685a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('email', sa.String, unique=True, index=True, nullable=False),
        sa.Column('first_name', sa.String, nullable=False),
        sa.Column('last_name', sa.String, nullable=False),
        sa.Column('hashed_password', sa.String, nullable=False),
        sa.Column('role', sa.Enum('admin', 'user', 'readonly', name='userrole'), 
                  server_default='user', nullable=False),
        sa.Column('is_active', sa.Boolean, server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('filename', sa.String, nullable=False),
        sa.Column('original_filename', sa.String, nullable=False),
        sa.Column('file_path', sa.String, nullable=False),
        sa.Column('file_size', sa.Integer, nullable=False),
        sa.Column('mime_type', sa.String, nullable=False),
        
        # Classification
        sa.Column('category', sa.String, server_default='non_classes'),
        sa.Column('confidence_score', sa.Float, server_default='0.0'),
        
        # OCR Results
        sa.Column('ocr_text', sa.Text, nullable=True),
        sa.Column('entities', sa.JSON, server_default='[]'),
        sa.Column('amount', sa.Float, nullable=True),
        sa.Column('document_date', sa.DateTime(timezone=True), nullable=True),
        
        # Metadata
        sa.Column('custom_tags', sa.JSON, server_default='[]'),
        sa.Column('embeddings_id', sa.String, nullable=True),
        
        # Relations
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create indexes
    op.create_index('ix_documents_user_id', 'documents', ['user_id'])
    op.create_index('ix_documents_category', 'documents', ['category'])
    op.create_index('ix_documents_created_at', 'documents', ['created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('ix_documents_created_at')
    op.drop_index('ix_documents_category')
    op.drop_index('ix_documents_user_id')
    
    # Drop tables
    op.drop_table('documents')
    op.drop_table('users')
    
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS userrole')
