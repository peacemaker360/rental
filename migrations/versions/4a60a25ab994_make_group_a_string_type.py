"""Make group a string type

Revision ID: 4a60a25ab994
Revises: 3d2a3c1b8337
Create Date: 2024-12-29 21:50:25.217481

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '4a60a25ab994'
down_revision = '3d2a3c1b8337'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('customer', schema=None) as batch_op:
        batch_op.alter_column('groups',
               existing_type=sqlite.JSON(),
               type_=sa.String(length=200),
               existing_nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('customer', schema=None) as batch_op:
        batch_op.alter_column('groups',
               existing_type=sa.String(length=200),
               type_=sqlite.JSON(),
               existing_nullable=True)

    # ### end Alembic commands ###
