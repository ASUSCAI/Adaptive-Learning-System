"""Add question_history column to user_categories

Revision ID: add_question_history
Revises: 
Create Date: 2023-03-31 09:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import BLOB

# revision identifiers, used by Alembic.
revision = 'add_question_history'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add column with PickleType compatibility for SQLite
    op.add_column('user_categories', sa.Column('question_history', sa.PickleType(), nullable=True))
    
    # SQLite doesn't support default values for BLOB/PickleType columns when adding a column,
    # so we need to update the values after adding the column
    op.execute("UPDATE user_categories SET question_history = '{}'")


def downgrade():
    # Drop the column
    op.drop_column('user_categories', 'question_history') 