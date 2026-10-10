"""SQLAlchemy ORM models.

Constraints are enforced twice on purpose: in app/validation.py (friendly
messages) and here at the database level (last line of defense against bad
writes from any code path).
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    false,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.validation import US_STATES, Sex

_STATE_LIST = ", ".join(f"'{code}'" for code in US_STATES)
_PHONE_CHECK = r"'^[2-9][0-9]{2}[2-9][0-9]{6}$'"


class Patient(Base):
    __tablename__ = "patients"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    date_of_birth: Mapped[date] = mapped_column(Date)
    sex: Mapped[Sex] = mapped_column(
        Enum(Sex, name="sex_enum", values_callable=lambda e: [m.value for m in e])
    )
    phone_number: Mapped[str] = mapped_column(String(10))
    email: Mapped[str | None] = mapped_column(String(254))
    address_line_1: Mapped[str] = mapped_column(String(100))
    address_line_2: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2))
    zip_code: Mapped[str] = mapped_column(String(10))
    insurance_provider: Mapped[str | None] = mapped_column(String(100))
    insurance_member_id: Mapped[str | None] = mapped_column(String(30))
    preferred_language: Mapped[str] = mapped_column(
        String(50), default="English", server_default="English"
    )
    emergency_contact_name: Mapped[str | None] = mapped_column(String(100))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(10))

    # Lets POST /patients be retried safely (e.g. by the voice agent) without
    # creating duplicate records.
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    calls: Mapped[list["CallSession"]] = relationship(back_populates="patient")

    __table_args__ = (
        CheckConstraint("char_length(first_name) BETWEEN 1 AND 50", name="ck_first_name_len"),
        CheckConstraint("char_length(last_name) BETWEEN 1 AND 50", name="ck_last_name_len"),
        CheckConstraint("date_of_birth >= DATE '1900-01-01'", name="ck_dob_min"),
        CheckConstraint(f"phone_number ~ {_PHONE_CHECK}", name="ck_phone_format"),
        CheckConstraint(
            f"emergency_contact_phone IS NULL OR emergency_contact_phone ~ {_PHONE_CHECK}",
            name="ck_emergency_phone_format",
        ),
        CheckConstraint(r"zip_code ~ '^[0-9]{5}(-[0-9]{4})?$'", name="ck_zip_format"),
        CheckConstraint(f"state IN ({_STATE_LIST})", name="ck_state_valid"),
        CheckConstraint("char_length(city) BETWEEN 1 AND 100", name="ck_city_len"),
        CheckConstraint(
            "insurance_member_id IS NULL OR insurance_member_id ~ '^[A-Z0-9]{1,30}$'",
            name="ck_member_id_format",
        ),
        CheckConstraint("email IS NULL OR position('@' in email) > 1", name="ck_email_format"),
        # Fast lookups for the API filters and returning-caller detection,
        # restricted to live (non-deleted) rows.
        Index("ix_patients_phone_live", "phone_number", postgresql_where=text("deleted_at IS NULL")),
        Index("ix_patients_last_name_lower", func.lower(last_name)),
        Index("ix_patients_dob", "date_of_birth"),
        Index("ix_patients_created_at", "created_at"),
    )


class CallSession(Base):
    """One phone call: the in-progress registration draft plus the call log.

    The voice agent's tools read and write the draft here, so the conversation
    state lives server-side (not only in the LLM context) and survives tool
    retries. After the call ends, Vapi's end-of-call report fills in the
    transcript and timing fields.
    """

    __tablename__ = "call_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    vapi_call_id: Mapped[str] = mapped_column(String(100), unique=True)
    caller_number: Mapped[str | None] = mapped_column(String(20))

    # collecting -> awaiting_confirmation -> completed | failed; or abandoned.
    state: Mapped[str] = mapped_column(String(30), default="collecting")
    # create: new patient. update: caller verified an existing record.
    mode: Mapped[str] = mapped_column(String(10), default="create")
    draft: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    # Hash of the draft at the moment it was read back to the caller.
    # submit_registration refuses to save anything that wasn't read back.
    reviewed_hash: Mapped[str | None] = mapped_column(String(64))
    matched_patient_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    verified_patient_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    verification_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Set when review_registration has bounced the agent back to offer the
    # optional fields; the offer is enforced by the server, not by a flag the LLM sets.
    optional_offered: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.patient_id")
    )
    # registered | updated | failed | abandoned | no_registration
    outcome: Mapped[str | None] = mapped_column(String(30))
    last_error: Mapped[str | None] = mapped_column(Text)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    ended_reason: Mapped[str | None] = mapped_column(String(100))
    transcript: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    patient: Mapped[Patient | None] = relationship(back_populates="calls")

    __table_args__ = (
        CheckConstraint(
            "state IN ('collecting', 'awaiting_confirmation', 'completed', 'failed', 'abandoned')",
            name="ck_call_state",
        ),
        CheckConstraint("mode IN ('create', 'update')", name="ck_call_mode"),
        Index("ix_call_sessions_created_at", "created_at"),
        Index("ix_call_sessions_patient_id", "patient_id"),
    )
