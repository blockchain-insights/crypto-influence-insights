"""Miner discovery and receipt tables

Revision ID: 001
Revises: 
Create Date: 2024-11-08 18:57:55.953664

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('miner_discoveries',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('uid', sa.Integer(), nullable=False),
    sa.Column('miner_key', sa.String(), nullable=False),
    sa.Column('token', sa.String(), nullable=False),
    sa.Column('miner_address', sa.String(), nullable=False),
    sa.Column('miner_ip_port', sa.String(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('rank', sa.Float(), nullable=False),
    sa.Column('failed_challenges', sa.Integer(), nullable=False),
    sa.Column('total_challenges', sa.Integer(), nullable=False),
    sa.Column('is_trusted', sa.Integer(), nullable=False),
    sa.Column('version', sa.Float(), nullable=False),
    sa.Column('graph_db', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__miner_discoveries')),
    sa.UniqueConstraint('miner_key', name=op.f('uq__miner_discoveries__miner_key'))
    )
    op.create_table('miner_receipts',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('request_id', sa.String(), nullable=False),
    sa.Column('miner_key', sa.String(), nullable=False),
    sa.Column('token', sa.String(), nullable=False),
    sa.Column('query_hash', sa.Text(), nullable=False),
    sa.Column('accepted', sa.Boolean(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__miner_receipts')),
    sa.UniqueConstraint('miner_key', 'request_id', name='uq_miner_key_request_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('miner_receipts')
    op.drop_table('miner_discoveries')
    # ### end Alembic commands ###