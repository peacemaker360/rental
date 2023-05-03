"""empty message

Revision ID: 4b0d137b00a0
Revises: 
Create Date: 2023-05-01 14:04:16.868932

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4b0d137b00a0'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('customer',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('firstname', sa.String(length=50), nullable=False),
    sa.Column('lastname', sa.String(length=50), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('customer', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_customer_created'), ['created'], unique=False)
        batch_op.create_index(batch_op.f('ix_customer_email'), ['email'], unique=True)

    op.create_table('instrument',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('brand', sa.String(length=50), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('serial', sa.String(length=50), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('price', sa.Float(), nullable=False),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('instrument', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_instrument_created'), ['created'], unique=False)

    op.create_table('rental',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('instrument_id', sa.Integer(), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['customer_id'], ['customer.id'], ),
    sa.ForeignKeyConstraint(['instrument_id'], ['instrument.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('rental', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_rental_created'), ['created'], unique=False)

    op.create_table('rental_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('rental_id', sa.Integer(), nullable=True),
    sa.Column('instrument_id', sa.Integer(), nullable=True),
    sa.Column('customer_id', sa.Integer(), nullable=True),
    sa.Column('start_date', sa.DateTime(), nullable=True),
    sa.Column('end_date', sa.DateTime(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['rental_id'], ['rental.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('rental_history', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_rental_history_timestamp'), ['timestamp'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('rental_history', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_rental_history_timestamp'))

    op.drop_table('rental_history')
    with op.batch_alter_table('rental', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_rental_created'))

    op.drop_table('rental')
    with op.batch_alter_table('instrument', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_instrument_created'))

    op.drop_table('instrument')
    with op.batch_alter_table('customer', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_customer_email'))
        batch_op.drop_index(batch_op.f('ix_customer_created'))

    op.drop_table('customer')
    # ### end Alembic commands ###