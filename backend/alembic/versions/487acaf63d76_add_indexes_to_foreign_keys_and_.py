"""add indexes to foreign keys and frequently queried columns

Revision ID: 487acaf63d76
Revises: 5a1c4dd3adb0
Create Date: 2026-05-19 16:42:11.085311

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "487acaf63d76"
down_revision: Union[str, Sequence[str], None] = "5a1c4dd3adb0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # documents table — collection_name is queried on every chat request
    op.create_index("ix_documents_collection_name", "documents", ["collection_name"])
    op.create_index("ix_documents_uploaded_at", "documents", ["uploaded_at"])

    # messages table — document_id is queried to load chat history
    op.create_index("ix_messages_document_id", "messages", ["document_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])

    # eval_results table — document_id is queried when saving eval results
    op.create_index("ix_eval_results_document_id", "eval_results", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_collection_name", "documents")
    op.drop_index("ix_documents_uploaded_at", "documents")
    op.drop_index("ix_messages_document_id", "messages")
    op.drop_index("ix_messages_created_at", "messages")
    op.drop_index("ix_eval_results_document_id", "eval_results")
