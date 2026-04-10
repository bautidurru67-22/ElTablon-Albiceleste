"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-04-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('username', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table('teams',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('nombre', sa.String(200), nullable=False),
        sa.Column('deporte', sa.String(50), nullable=False),
        sa.Column('liga', sa.String(200), nullable=True),
        sa.Column('pais', sa.String(100), server_default='Argentina'),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_teams_slug',         'teams', ['slug'],    unique=True)
    op.create_index('ix_teams_deporte',      'teams', ['deporte'])
    op.create_index('ix_teams_deporte_liga', 'teams', ['deporte', 'liga'])

    op.create_table('players',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('nombre', sa.String(200), nullable=False),
        sa.Column('deporte', sa.String(50), nullable=False),
        sa.Column('equipo_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=True),
        sa.Column('nacionalidad', sa.String(100), server_default='Argentina'),
        sa.Column('posicion', sa.String(100), nullable=True),
        sa.Column('ranking', sa.Integer(), nullable=True),
        sa.Column('stat_label', sa.String(50), nullable=True),
        sa.Column('stat_value', sa.String(50), nullable=True),
        sa.Column('foto_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_players_slug',    'players', ['slug'],    unique=True)
    op.create_index('ix_players_deporte', 'players', ['deporte'])

    op.create_table('matches',
        sa.Column('id', sa.String(200), nullable=False),
        sa.Column('deporte', sa.String(50), nullable=False),
        sa.Column('competition', sa.String(200), nullable=False),
        sa.Column('equipo_local_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=True),
        sa.Column('equipo_visitante_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=True),
        sa.Column('equipo_local_nombre', sa.String(200), nullable=False),
        sa.Column('equipo_visitante_nombre', sa.String(200), nullable=False),
        sa.Column('goles_local', sa.Integer(), nullable=True),
        sa.Column('goles_visitante', sa.Integer(), nullable=True),
        sa.Column('score_detail', sa.String(100), nullable=True),
        sa.Column('estado', sa.String(20), nullable=False, server_default='upcoming'),
        sa.Column('minuto', sa.String(20), nullable=True),
        sa.Column('fecha', sa.DateTime(timezone=True), nullable=True),
        sa.Column('hora_arg', sa.String(10), nullable=True),
        sa.Column('argentina_relevance', sa.String(20), nullable=False, server_default='none'),
        sa.Column('argentina_team', sa.String(200), nullable=True),
        sa.Column('broadcast', sa.String(200), nullable=True),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_matches_deporte_estado', 'matches', ['deporte', 'estado'])
    op.create_index('ix_matches_fecha_estado',   'matches', ['fecha',   'estado'])
    op.create_index('ix_matches_argentina',      'matches', ['argentina_relevance', 'estado'])

    op.create_table('live_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('partido_id', sa.String(200), sa.ForeignKey('matches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tipo_evento', sa.String(50), nullable=False),
        sa.Column('minuto', sa.String(20), nullable=True),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('jugador', sa.String(200), nullable=True),
        sa.Column('equipo', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_live_events_partido', 'live_events', ['partido_id'])

    op.create_table('favorites',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('entity_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'tipo', 'entity_id', name='uq_favorite_user_entity'),
    )
    op.create_index('ix_favorites_user_tipo', 'favorites', ['user_id', 'tipo'])


def downgrade() -> None:
    op.drop_table('favorites')
    op.drop_table('live_events')
    op.drop_table('matches')
    op.drop_table('players')
    op.drop_table('teams')
    op.drop_table('users')
