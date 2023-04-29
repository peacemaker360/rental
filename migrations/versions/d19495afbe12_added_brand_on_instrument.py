"""added brand on instrument

Revision ID: d19495afbe12
Revises: 96e69a3d2787
Create Date: 2023-04-28 16:41:02.340959

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd19495afbe12'
down_revision = '96e69a3d2787'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('instrument', schema=None) as batch_op:
        batch_op.add_column(sa.Column('brand', sa.String(length=50), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('instrument', schema=None) as batch_op:
        batch_op.drop_column('brand')

    # ### end Alembic commands ###
