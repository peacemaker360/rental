"""Initial migration

Revision ID: 9fcdd83221b6
Revises: 
Create Date: 2025-03-09 11:33:54.880289

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9fcdd83221b6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('rental', schema=None) as batch_op:
        batch_op.add_column(sa.Column('return_date', sa.Date(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('rental', schema=None) as batch_op:
        batch_op.drop_column('return_date')

    # ### end Alembic commands ###
