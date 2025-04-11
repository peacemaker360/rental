"""Add year_of_purchase to instrument model

Revision ID: 6edc46cf98ff
Revises: 4621b5848edf
Create Date: 2025-04-11 18:21:52.642032

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6edc46cf98ff'
down_revision = '4621b5848edf'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('note')
    with op.batch_alter_table('instrument', schema=None) as batch_op:
        batch_op.add_column(sa.Column('year_of_purchase', sa.Date(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('instrument', schema=None) as batch_op:
        batch_op.drop_column('year_of_purchase')

    op.create_table('note',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('instrument_id', sa.INTEGER(), nullable=False),
    sa.Column('content', sa.TEXT(), nullable=False),
    sa.Column('type', sa.VARCHAR(length=50), nullable=False),
    sa.Column('created', sa.DATETIME(), nullable=True),
    sa.Column('updated', sa.DATETIME(), nullable=True),
    sa.Column('created_by', sa.INTEGER(), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], name='fk_note_created_by_user'),
    sa.ForeignKeyConstraint(['instrument_id'], ['instrument.id'], name='fk_note_instrument_id_instrument'),
    sa.PrimaryKeyConstraint('id', name='pk_note')
    )
    # ### end Alembic commands ###
