"""Initial schema including firebase_uid in users table.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-07-23 09:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('firebase_uid', sa.String(length=128), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('avatar_url', sa.String(length=512), nullable=True, server_default=''),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_firebase_uid', 'users', ['firebase_uid'], unique=True)

    # Collections table
    op.create_table(
        'collections',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True, server_default='#6366f1'),
        sa.Column('icon', sa.String(length=50), nullable=True, server_default='folder'),
        sa.Column('document_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_collections_user_id', 'collections', ['user_id'], unique=False)

    # Documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('collection_id', sa.String(length=36), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('file_type', sa.Enum('PDF', 'DOCX', 'TXT', name='documenttype'), nullable=True),
        sa.Column('status', sa.Enum('UPLOADED', 'PARSING', 'PARSED', 'INDEXING', 'INDEXED', 'FAILED', name='documentstatus'), nullable=True),
        sa.Column('title', sa.String(length=512), nullable=True),
        sa.Column('authors', sa.JSON(), nullable=True),
        sa.Column('abstract', sa.Text(), nullable=True),
        sa.Column('publication_date', sa.String(length=50), nullable=True),
        sa.Column('journal', sa.String(length=255), nullable=True),
        sa.Column('doi', sa.String(length=255), nullable=True),
        sa.Column('keywords', sa.JSON(), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('word_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('chunk_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_documents_collection_id', 'documents', ['collection_id'], unique=False)
    op.create_index('ix_documents_status', 'documents', ['status'], unique=False)
    op.create_index('ix_documents_user_id', 'documents', ['user_id'], unique=False)

    # Chunks table
    op.create_table(
        'chunks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('parent_content', sa.Text(), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('section_header', sa.String(length=255), nullable=True),
        sa.Column('chunk_index', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('token_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chunks_document_id', 'chunks', ['document_id'], unique=False)

    # Conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True, server_default='New Conversation'),
        sa.Column('scope', sa.Enum('DOCUMENT', 'COLLECTION', 'WORKSPACE', name='conversationscope'), nullable=True),
        sa.Column('document_ids', sa.JSON(), nullable=True),
        sa.Column('collection_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conversations_collection_id', 'conversations', ['collection_id'], unique=False)
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'], unique=False)

    # Messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.Enum('USER', 'ASSISTANT', 'SYSTEM', name='messagerole'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('citations', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'], unique=False)

    # Research Notes table
    op.create_table(
        'research_notes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('document_title', sa.String(length=512), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('snippet', sa.Text(), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_research_notes_document_id', 'research_notes', ['document_id'], unique=False)
    op.create_index('ix_research_notes_user_id', 'research_notes', ['user_id'], unique=False)

    # Timeline Events table
    op.create_table(
        'timeline_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_timeline_events_user_id', 'timeline_events', ['user_id'], unique=False)

    # Workspace Settings table
    op.create_table(
        'workspace_settings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('theme', sa.String(length=20), nullable=True, server_default='light'),
        sa.Column('selected_document_ids', sa.JSON(), nullable=True),
        sa.Column('active_document_id', sa.String(length=36), nullable=True),
        sa.Column('active_conversation_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workspace_settings_user_id', 'workspace_settings', ['user_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_workspace_settings_user_id', table_name='workspace_settings')
    op.drop_table('workspace_settings')
    op.drop_index('ix_timeline_events_user_id', table_name='timeline_events')
    op.drop_table('timeline_events')
    op.drop_index('ix_research_notes_user_id', table_name='research_notes')
    op.drop_index('ix_research_notes_document_id', table_name='research_notes')
    op.drop_table('research_notes')
    op.drop_index('ix_messages_conversation_id', table_name='messages')
    op.drop_table('messages')
    op.drop_index('ix_conversations_user_id', table_name='conversations')
    op.drop_index('ix_conversations_collection_id', table_name='conversations')
    op.drop_table('conversations')
    op.drop_index('ix_chunks_document_id', table_name='chunks')
    op.drop_table('chunks')
    op.drop_index('ix_documents_user_id', table_name='documents')
    op.drop_index('ix_documents_status', table_name='documents')
    op.drop_index('ix_documents_collection_id', table_name='documents')
    op.drop_table('documents')
    op.drop_index('ix_collections_user_id', table_name='collections')
    op.drop_table('collections')
    op.drop_index('ix_users_firebase_uid', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
