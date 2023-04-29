"""added is_available logic

Revision ID: 0b1683ec0a3b
Revises: d19495afbe12
Create Date: 2023-04-28 18:25:23.185141

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0b1683ec0a3b'
down_revision = 'd19495afbe12'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('rental', schema=None) as batch_op:
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.alter_column('end_date',
               existing_type=sa.DATE(),
               nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('rental', schema=None) as batch_op:
        batch_op.alter_column('end_date',
               existing_type=sa.DATE(),
               nullable=False)
        batch_op.drop_column('description')

    # ### end Alembic commands ###
