"""Initial migration with naming convention

Revision ID: 5e595eaacfcf
Revises: 9fcdd83221b6
Create Date: 2025-03-15 15:36:49.550460

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5e595eaacfcf'
down_revision = '9fcdd83221b6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('rental_history', schema=None) as batch_op:
        batch_op.alter_column('instrument_id',
               existing_type=sa.INTEGER(),
               nullable=True)
        batch_op.alter_column('customer_id',
               existing_type=sa.INTEGER(),
               nullable=True)
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('rental_history', schema=None) as batch_op:
        batch_op.create_foreign_key(None, 'instrument', ['instrument_id'], ['id'])
        batch_op.create_foreign_key(None, 'customer', ['customer_id'], ['id'])
        batch_op.create_foreign_key(None, 'rental', ['rental_id'], ['id'])
        batch_op.alter_column('customer_id',
               existing_type=sa.INTEGER(),
               nullable=False)
        batch_op.alter_column('instrument_id',
               existing_type=sa.INTEGER(),
               nullable=False)

    # ### end Alembic commands ###
