"""Initial BOA schema

Revision ID: 001_initial
Revises: 
Create Date: 2024-12-31

Creates all BOA tables:
- processes
- campaigns
- observations
- iterations
- proposals
- decisions
- checkpoints
- artifacts
- jobs
- campaign_locks
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create processes table
    op.create_table(
        'processes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('spec_yaml', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('spec_parsed', sa.JSON(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_processes_name'), 'processes', ['name'], unique=False)
    
    # Create campaigns table
    op.create_table(
        'campaigns',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('process_id', sa.Uuid(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('status', sa.Enum('CREATED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED', name='campaignstatus'), nullable=False),
        sa.Column('strategy_config', sa.JSON(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['process_id'], ['processes.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_campaigns_name'), 'campaigns', ['name'], unique=False)
    op.create_index(op.f('ix_campaigns_process_id'), 'campaigns', ['process_id'], unique=False)
    op.create_index(op.f('ix_campaigns_status'), 'campaigns', ['status'], unique=False)
    
    # Create observations table
    op.create_table(
        'observations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('campaign_id', sa.Uuid(), nullable=False),
        sa.Column('x_raw', sa.JSON(), nullable=False),
        sa.Column('x_encoded', sa.JSON(), nullable=True),
        sa.Column('y', sa.JSON(), nullable=False),
        sa.Column('source', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('observed_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_observations_campaign_id'), 'observations', ['campaign_id'], unique=False)
    
    # Create iterations table
    op.create_table(
        'iterations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('campaign_id', sa.Uuid(), nullable=False),
        sa.Column('index', sa.Integer(), nullable=False),
        sa.Column('dataset_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_iterations_campaign_id'), 'iterations', ['campaign_id'], unique=False)
    
    # Create proposals table
    op.create_table(
        'proposals',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('iteration_id', sa.Uuid(), nullable=False),
        sa.Column('strategy_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('candidates_raw', sa.JSON(), nullable=False),
        sa.Column('candidates_encoded', sa.JSON(), nullable=True),
        sa.Column('acq_values', sa.JSON(), nullable=True),
        sa.Column('predictions', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['iteration_id'], ['iterations.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_proposals_iteration_id'), 'proposals', ['iteration_id'], unique=False)
    op.create_index(op.f('ix_proposals_strategy_name'), 'proposals', ['strategy_name'], unique=False)
    
    # Create decisions table
    op.create_table(
        'decisions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('iteration_id', sa.Uuid(), nullable=False),
        sa.Column('accepted', sa.JSON(), nullable=False),
        sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['iteration_id'], ['iterations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('iteration_id'),
    )
    op.create_index(op.f('ix_decisions_iteration_id'), 'decisions', ['iteration_id'], unique=True)
    
    # Create checkpoints table
    op.create_table(
        'checkpoints',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('campaign_id', sa.Uuid(), nullable=False),
        sa.Column('iteration_id', sa.Uuid(), nullable=True),
        sa.Column('path', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.ForeignKeyConstraint(['iteration_id'], ['iterations.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_checkpoints_campaign_id'), 'checkpoints', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_checkpoints_iteration_id'), 'checkpoints', ['iteration_id'], unique=False)
    
    # Create artifacts table
    op.create_table(
        'artifacts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('campaign_id', sa.Uuid(), nullable=False),
        sa.Column('iteration_id', sa.Uuid(), nullable=True),
        sa.Column('artifact_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('path', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('content_type', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.ForeignKeyConstraint(['iteration_id'], ['iterations.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_artifacts_artifact_type'), 'artifacts', ['artifact_type'], unique=False)
    op.create_index(op.f('ix_artifacts_campaign_id'), 'artifacts', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_artifacts_iteration_id'), 'artifacts', ['iteration_id'], unique=False)
    
    # Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('campaign_id', sa.Uuid(), nullable=True),
        sa.Column('job_type', sa.Enum('PROPOSE', 'BENCHMARK', 'EXPORT', 'IMPORT', name='jobtype'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', name='jobstatus'), nullable=False),
        sa.Column('params', sa.JSON(), nullable=False),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('progress', sa.Float(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_jobs_campaign_id'), 'jobs', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_jobs_job_type'), 'jobs', ['job_type'], unique=False)
    op.create_index(op.f('ix_jobs_status'), 'jobs', ['status'], unique=False)
    
    # Create campaign_locks table
    op.create_table(
        'campaign_locks',
        sa.Column('campaign_id', sa.Uuid(), nullable=False),
        sa.Column('locked_by', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('locked_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('campaign_id'),
    )


def downgrade() -> None:
    op.drop_table('campaign_locks')
    op.drop_table('jobs')
    op.drop_table('artifacts')
    op.drop_table('checkpoints')
    op.drop_table('decisions')
    op.drop_table('proposals')
    op.drop_table('iterations')
    op.drop_table('observations')
    op.drop_table('campaigns')
    op.drop_table('processes')






