"""initial_schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-26 01:40:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=30), nullable=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=True),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('role', sa.String(length=20), server_default='customer', nullable=False),
        sa.Column('avatar', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('address', sa.String(length=300), nullable=True),
        sa.Column('rating', sa.Float(), server_default='5.0', nullable=False),
        sa.Column('total_orders', sa.Integer(), server_default='0', nullable=False),
        sa.Column('google_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('phone'),
        sa.UniqueConstraint('google_id'),
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. service_categories table
    op.create_table(
        'service_categories',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('icon_name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=300), nullable=False),
        sa.Column('diagnostic_fee', sa.Float(), nullable=False),
        sa.Column('estimated_arrival_min', sa.Integer(), nullable=False),
        sa.Column('popular_problems', sa.JSON(), nullable=False),
        sa.Column('active_workers_count', sa.Integer(), server_default='18', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # 3. worker_profiles table
    op.create_table(
        'worker_profiles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('category_id', sa.String(length=100), nullable=False),
        sa.Column('skills', sa.JSON(), nullable=False),
        sa.Column('experience_years', sa.Integer(), server_default='3', nullable=False),
        sa.Column('is_online', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('verification_status', sa.String(length=30), server_default='VERIFIED', nullable=False),
        sa.Column('aadhaar_verified', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('police_cleared', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('skill_audited', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('badge_title', sa.String(length=100), server_default='Master Craftsman', nullable=False),
        sa.Column('latitude', sa.Float(), server_default='12.9716', nullable=False),
        sa.Column('longitude', sa.Float(), server_default='77.5946', nullable=False),
        sa.Column('current_area', sa.String(length=200), server_default='Indiranagar, Bengaluru', nullable=False),
        sa.Column('acceptance_rate', sa.Float(), server_default='98.5', nullable=False),
        sa.Column('completion_rate', sa.Float(), server_default='99.0', nullable=False),
        sa.Column('completed_jobs', sa.Integer(), server_default='0', nullable=False),
        sa.Column('reviews_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('rating', sa.Float(), server_default='4.88', nullable=False),
        sa.Column('today_earnings', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('week_earnings', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('month_earnings', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('current_active_job_id', sa.String(length=50), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )

    # 4. service_jobs table
    op.create_table(
        'service_jobs',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('customer_id', sa.String(length=36), nullable=False),
        sa.Column('worker_id', sa.String(length=36), nullable=True),
        sa.Column('category_id', sa.String(length=50), nullable=False),
        sa.Column('category_name', sa.String(length=100), nullable=False),
        sa.Column('problem_type', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('photos', sa.JSON(), nullable=False),
        sa.Column('urgency', sa.String(length=20), server_default='NORMAL', nullable=False),
        sa.Column('status', sa.String(length=30), server_default='SEARCHING', nullable=False),
        sa.Column('customer_address', sa.String(length=300), nullable=False),
        sa.Column('customer_lat', sa.Float(), nullable=False),
        sa.Column('customer_lng', sa.Float(), nullable=False),
        sa.Column('worker_distance_km', sa.Float(), nullable=True),
        sa.Column('worker_eta_minutes', sa.Integer(), nullable=True),
        sa.Column('diagnosis_notes', sa.Text(), nullable=True),
        sa.Column('before_photos', sa.JSON(), nullable=False),
        sa.Column('after_photos', sa.JSON(), nullable=False),
        sa.Column('parts_receipts', sa.JSON(), nullable=False),
        sa.Column('worker_completion_notes', sa.Text(), nullable=True),
        sa.Column('cancellation_reason', sa.String(length=300), nullable=True),
        sa.Column('is_sos_triggered', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['users.id']),
        sa.ForeignKeyConstraint(['worker_id'], ['users.id']),
        sa.ForeignKeyConstraint(['category_id'], ['service_categories.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_service_jobs_status'), 'service_jobs', ['status'], unique=False)

    # 5. timeline_events table
    op.create_table(
        'timeline_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('description', sa.String(length=300), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['service_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 6. quotes table
    op.create_table(
        'quotes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=50), nullable=False),
        sa.Column('diagnostic_fee', sa.Float(), nullable=False),
        sa.Column('labour', sa.Float(), nullable=False),
        sa.Column('parts', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('platform_fee', sa.Float(), server_default='49.0', nullable=False),
        sa.Column('tax', sa.Float(), nullable=False),
        sa.Column('total', sa.Float(), nullable=False),
        sa.Column('parts_description', sa.Text(), nullable=True),
        sa.Column('is_approved', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('rejection_reason', sa.String(length=300), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['service_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id'),
    )

    # 7. payments table
    op.create_table(
        'payments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=50), nullable=False),
        sa.Column('customer_id', sa.String(length=36), nullable=False),
        sa.Column('worker_id', sa.String(length=36), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('status', sa.String(length=30), server_default='PENDING', nullable=False),
        sa.Column('method', sa.String(length=30), server_default='UPI', nullable=False),
        sa.Column('gateway', sa.String(length=30), server_default='RAZORPAY', nullable=False),
        sa.Column('gateway_order_id', sa.String(length=100), nullable=True),
        sa.Column('gateway_payment_id', sa.String(length=100), nullable=True),
        sa.Column('gateway_signature', sa.String(length=255), nullable=True),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('breakdown', sa.JSON(), nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('escrow_released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['service_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['users.id']),
        sa.ForeignKeyConstraint(['worker_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id'),
        sa.UniqueConstraint('invoice_number'),
    )

    # 8. worker_payouts table
    op.create_table(
        'worker_payouts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('worker_id', sa.String(length=36), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='COMPLETED', nullable=False),
        sa.Column('payout_method', sa.String(length=50), server_default='UPI_INSTANT', nullable=False),
        sa.Column('reference_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['worker_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # 9. job_ratings table
    op.create_table(
        'job_ratings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=50), nullable=False),
        sa.Column('customer_id', sa.String(length=36), nullable=False),
        sa.Column('worker_id', sa.String(length=36), nullable=False),
        sa.Column('overall', sa.Float(), nullable=False),
        sa.Column('skill', sa.Float(), server_default='5.0', nullable=False),
        sa.Column('punctuality', sa.Float(), server_default='5.0', nullable=False),
        sa.Column('communication', sa.Float(), server_default='5.0', nullable=False),
        sa.Column('pricing_transparency', sa.Float(), server_default='5.0', nullable=False),
        sa.Column('review_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['service_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['users.id']),
        sa.ForeignKeyConstraint(['worker_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id'),
    )

    # 10. dispute_records table
    op.create_table(
        'dispute_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=50), nullable=False),
        sa.Column('raised_by_user_id', sa.String(length=36), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='PENDING', nullable=False),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('refund_amount', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['service_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['raised_by_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id'),
    )

    # 11. sos_incidents table
    op.create_table(
        'sos_incidents',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('job_id', sa.String(length=50), nullable=True),
        sa.Column('triggered_by_user_id', sa.String(length=36), nullable=False),
        sa.Column('customer_name', sa.String(length=150), nullable=False),
        sa.Column('worker_name', sa.String(length=150), server_default='Quick Reaction Fleet', nullable=False),
        sa.Column('contact_number', sa.String(length=30), nullable=False),
        sa.Column('location', sa.String(length=300), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('urgency', sa.String(length=20), server_default='CRITICAL', nullable=False),
        sa.Column('status', sa.String(length=30), server_default='TRIGGERED', nullable=False),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['service_jobs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['triggered_by_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('sos_incidents')
    op.drop_table('dispute_records')
    op.drop_table('job_ratings')
    op.drop_table('worker_payouts')
    op.drop_table('payments')
    op.drop_table('quotes')
    op.drop_table('timeline_events')
    op.drop_table('service_jobs')
    op.drop_table('worker_profiles')
    op.drop_table('service_categories')
    op.drop_table('users')
