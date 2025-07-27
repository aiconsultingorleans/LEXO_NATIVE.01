"""
Add batch operations and rollback support

Revision ID: add_batch_operations
Revises: b342af89685a
Create Date: 2025-01-27 20:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_batch_operations'
down_revision = 'b342af89685a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create tables for batch operations and rollback management"""
    
    # Create batch_operations table
    op.create_table(
        'batch_operations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('batch_name', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('total_files', sa.Integer(), nullable=False),
        sa.Column('pipeline_type', sa.String(), nullable=False),
        sa.Column('auto_rollback_on_error', sa.Boolean(), nullable=True),
        sa.Column('files_processed', sa.Integer(), nullable=True),
        sa.Column('files_succeeded', sa.Integer(), nullable=True),
        sa.Column('files_failed', sa.Integer(), nullable=True),
        sa.Column('current_file_index', sa.Integer(), nullable=True),
        sa.Column('progress_percentage', sa.Float(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_completion', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_time_seconds', sa.Float(), nullable=True),
        sa.Column('can_rollback', sa.Boolean(), nullable=True),
        sa.Column('rollback_snapshot_id', sa.String(), nullable=True),
        sa.Column('rollback_reason', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processing_logs', sa.JSON(), nullable=True),
        sa.Column('summary_stats', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for batch_operations
    op.create_index('ix_batch_operations_id', 'batch_operations', ['id'])
    op.create_index('ix_batch_operations_status', 'batch_operations', ['status'])
    op.create_index('ix_batch_operations_user_id', 'batch_operations', ['user_id'])
    
    # Create batch_documents table
    op.create_table(
        'batch_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('batch_operation_id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('original_filename', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(), nullable=False),
        sa.Column('processing_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('processing_time_seconds', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('original_file_path', sa.String(), nullable=True),
        sa.Column('backup_file_path', sa.String(), nullable=True),
        sa.Column('pre_processing_snapshot', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['batch_operation_id'], ['batch_operations.id'], ),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for batch_documents
    op.create_index('ix_batch_documents_id', 'batch_documents', ['id'])
    op.create_index('ix_batch_documents_status', 'batch_documents', ['status'])
    op.create_index('ix_batch_documents_batch_operation_id', 'batch_documents', ['batch_operation_id'])
    
    # Create rollback_snapshots table
    op.create_table(
        'rollback_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('snapshot_id', sa.String(), nullable=False),
        sa.Column('batch_operation_id', sa.Integer(), nullable=False),
        sa.Column('snapshot_type', sa.String(), nullable=False),
        sa.Column('filesystem_state', sa.JSON(), nullable=True),
        sa.Column('database_state', sa.JSON(), nullable=True),
        sa.Column('auto_cleanup', sa.Boolean(), nullable=True),
        sa.Column('cleanup_after_days', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['batch_operation_id'], ['batch_operations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('snapshot_id')
    )
    
    # Create indexes for rollback_snapshots
    op.create_index('ix_rollback_snapshots_id', 'rollback_snapshots', ['id'])
    op.create_index('ix_rollback_snapshots_snapshot_id', 'rollback_snapshots', ['snapshot_id'])
    op.create_index('ix_rollback_snapshots_batch_operation_id', 'rollback_snapshots', ['batch_operation_id'])
    
    # Set default values for existing columns
    op.execute("UPDATE batch_operations SET status = 'pending' WHERE status IS NULL")
    op.execute("UPDATE batch_operations SET total_files = 0 WHERE total_files IS NULL")
    op.execute("UPDATE batch_operations SET pipeline_type = 'mistral' WHERE pipeline_type IS NULL")
    op.execute("UPDATE batch_operations SET auto_rollback_on_error = true WHERE auto_rollback_on_error IS NULL")
    op.execute("UPDATE batch_operations SET files_processed = 0 WHERE files_processed IS NULL")
    op.execute("UPDATE batch_operations SET files_succeeded = 0 WHERE files_succeeded IS NULL")
    op.execute("UPDATE batch_operations SET files_failed = 0 WHERE files_failed IS NULL")
    op.execute("UPDATE batch_operations SET current_file_index = 0 WHERE current_file_index IS NULL")
    op.execute("UPDATE batch_operations SET progress_percentage = 0.0 WHERE progress_percentage IS NULL")
    op.execute("UPDATE batch_operations SET can_rollback = true WHERE can_rollback IS NULL")
    op.execute("UPDATE batch_operations SET processing_logs = '[]'::json WHERE processing_logs IS NULL")
    op.execute("UPDATE batch_operations SET summary_stats = '{}'::json WHERE summary_stats IS NULL")
    
    op.execute("UPDATE batch_documents SET status = 'pending' WHERE status IS NULL")
    op.execute("UPDATE batch_documents SET retry_count = 0 WHERE retry_count IS NULL")
    op.execute("UPDATE batch_documents SET max_retries = 3 WHERE max_retries IS NULL")
    op.execute("UPDATE batch_documents SET pre_processing_snapshot = '{}'::json WHERE pre_processing_snapshot IS NULL")
    
    op.execute("UPDATE rollback_snapshots SET auto_cleanup = true WHERE auto_cleanup IS NULL")
    op.execute("UPDATE rollback_snapshots SET cleanup_after_days = 30 WHERE cleanup_after_days IS NULL")
    op.execute("UPDATE rollback_snapshots SET filesystem_state = '{}'::json WHERE filesystem_state IS NULL")
    op.execute("UPDATE rollback_snapshots SET database_state = '{}'::json WHERE database_state IS NULL")


def downgrade() -> None:
    """Drop batch operations tables"""
    
    # Drop indexes first
    op.drop_index('ix_rollback_snapshots_batch_operation_id', table_name='rollback_snapshots')
    op.drop_index('ix_rollback_snapshots_snapshot_id', table_name='rollback_snapshots')
    op.drop_index('ix_rollback_snapshots_id', table_name='rollback_snapshots')
    
    op.drop_index('ix_batch_documents_batch_operation_id', table_name='batch_documents')
    op.drop_index('ix_batch_documents_status', table_name='batch_documents')
    op.drop_index('ix_batch_documents_id', table_name='batch_documents')
    
    op.drop_index('ix_batch_operations_user_id', table_name='batch_operations')
    op.drop_index('ix_batch_operations_status', table_name='batch_operations')
    op.drop_index('ix_batch_operations_id', table_name='batch_operations')
    
    # Drop tables
    op.drop_table('rollback_snapshots')
    op.drop_table('batch_documents')
    op.drop_table('batch_operations')