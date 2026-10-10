"""initial schema: patients and call_sessions

Revision ID: 0001
Revises: 
Create Date: 2026-10-10 20:45:04.152246
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('patients',
    sa.Column('patient_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('first_name', sa.String(length=50), nullable=False),
    sa.Column('last_name', sa.String(length=50), nullable=False),
    sa.Column('date_of_birth', sa.Date(), nullable=False),
    sa.Column('sex', sa.Enum('Male', 'Female', 'Other', 'Decline to Answer', name='sex_enum'), nullable=False),
    sa.Column('phone_number', sa.String(length=10), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=True),
    sa.Column('address_line_1', sa.String(length=100), nullable=False),
    sa.Column('address_line_2', sa.String(length=100), nullable=True),
    sa.Column('city', sa.String(length=100), nullable=False),
    sa.Column('state', sa.String(length=2), nullable=False),
    sa.Column('zip_code', sa.String(length=10), nullable=False),
    sa.Column('insurance_provider', sa.String(length=100), nullable=True),
    sa.Column('insurance_member_id', sa.String(length=30), nullable=True),
    sa.Column('preferred_language', sa.String(length=50), server_default='English', nullable=False),
    sa.Column('emergency_contact_name', sa.String(length=100), nullable=True),
    sa.Column('emergency_contact_phone', sa.String(length=10), nullable=True),
    sa.Column('idempotency_key', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("date_of_birth >= DATE '1900-01-01'", name='ck_dob_min'),
    sa.CheckConstraint("email IS NULL OR position('@' in email) > 1", name='ck_email_format'),
    sa.CheckConstraint("emergency_contact_phone IS NULL OR emergency_contact_phone ~ '^[2-9][0-9]{2}[2-9][0-9]{6}$'", name='ck_emergency_phone_format'),
    sa.CheckConstraint("insurance_member_id IS NULL OR insurance_member_id ~ '^[A-Z0-9]{1,30}$'", name='ck_member_id_format'),
    sa.CheckConstraint("phone_number ~ '^[2-9][0-9]{2}[2-9][0-9]{6}$'", name='ck_phone_format'),
    sa.CheckConstraint("state IN ('AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC', 'PR', 'GU', 'VI', 'AS', 'MP')", name='ck_state_valid'),
    sa.CheckConstraint("zip_code ~ '^[0-9]{5}(-[0-9]{4})?$'", name='ck_zip_format'),
    sa.CheckConstraint('char_length(city) BETWEEN 1 AND 100', name='ck_city_len'),
    sa.CheckConstraint('char_length(first_name) BETWEEN 1 AND 50', name='ck_first_name_len'),
    sa.CheckConstraint('char_length(last_name) BETWEEN 1 AND 50', name='ck_last_name_len'),
    sa.PrimaryKeyConstraint('patient_id'),
    sa.UniqueConstraint('idempotency_key')
    )
    op.create_index('ix_patients_created_at', 'patients', ['created_at'], unique=False)
    op.create_index('ix_patients_dob', 'patients', ['date_of_birth'], unique=False)
    op.create_index('ix_patients_last_name_lower', 'patients', [sa.literal_column('lower(last_name)')], unique=False)
    op.create_index('ix_patients_phone_live', 'patients', ['phone_number'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_table('call_sessions',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('vapi_call_id', sa.String(length=100), nullable=False),
    sa.Column('caller_number', sa.String(length=20), nullable=True),
    sa.Column('state', sa.String(length=30), nullable=False),
    sa.Column('mode', sa.String(length=10), nullable=False),
    sa.Column('draft', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('reviewed_hash', sa.String(length=64), nullable=True),
    sa.Column('matched_patient_id', sa.UUID(), nullable=True),
    sa.Column('verified_patient_id', sa.UUID(), nullable=True),
    sa.Column('verification_attempts', sa.Integer(), server_default='0', nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=True),
    sa.Column('outcome', sa.String(length=30), nullable=True),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('duration_seconds', sa.Integer(), nullable=True),
    sa.Column('ended_reason', sa.String(length=100), nullable=True),
    sa.Column('transcript', sa.Text(), nullable=True),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("mode IN ('create', 'update')", name='ck_call_mode'),
    sa.CheckConstraint("state IN ('collecting', 'awaiting_confirmation', 'completed', 'failed', 'abandoned')", name='ck_call_state'),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('vapi_call_id')
    )
    op.create_index('ix_call_sessions_created_at', 'call_sessions', ['created_at'], unique=False)
    op.create_index('ix_call_sessions_patient_id', 'call_sessions', ['patient_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_call_sessions_patient_id', table_name='call_sessions')
    op.drop_index('ix_call_sessions_created_at', table_name='call_sessions')
    op.drop_table('call_sessions')
    op.drop_index('ix_patients_phone_live', table_name='patients', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index('ix_patients_last_name_lower', table_name='patients')
    op.drop_index('ix_patients_dob', table_name='patients')
    op.drop_index('ix_patients_created_at', table_name='patients')
    op.drop_table('patients')
    sa.Enum(name='sex_enum').drop(op.get_bind(), checkfirst=True)
